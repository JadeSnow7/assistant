# PlatformDetection.cmake - 平台检测和特定优化配置
# 基于设计文档实现跨平台检测和优化策略

cmake_minimum_required(VERSION 3.20)

# 设置平台检测变量
set(HUSHELL_PLATFORM_DETECTED FALSE)

# ==================== 平台检测 ====================

# 检测操作系统
if(WIN32)
    set(PLATFORM_NAME "windows")
    set(HUSHELL_PLATFORM_WINDOWS TRUE)
    add_compile_definitions(HUSHELL_PLATFORM_WINDOWS)
    message(STATUS "Detected platform: Windows")
elseif(APPLE)
    set(PLATFORM_NAME "macos")
    set(HUSHELL_PLATFORM_MACOS TRUE)
    add_compile_definitions(HUSHELL_PLATFORM_MACOS)
    message(STATUS "Detected platform: macOS")
elseif(UNIX AND NOT APPLE)
    set(PLATFORM_NAME "linux")
    set(HUSHELL_PLATFORM_LINUX TRUE)
    add_compile_definitions(HUSHELL_PLATFORM_LINUX)
    message(STATUS "Detected platform: Linux")
else()
    message(FATAL_ERROR "Unsupported platform detected")
endif()

set(HUSHELL_PLATFORM_DETECTED TRUE)

# ==================== 架构检测 ====================

# 检测CPU架构
if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    set(HUSHELL_ARCH_X64 TRUE)
    add_compile_definitions(HUSHELL_ARCH_X64)
    message(STATUS "Architecture: x86_64")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "i386|i686")
    set(HUSHELL_ARCH_X86 TRUE)
    add_compile_definitions(HUSHELL_ARCH_X86)
    message(STATUS "Architecture: x86")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
    set(HUSHELL_ARCH_ARM64 TRUE)
    add_compile_definitions(HUSHELL_ARCH_ARM64)
    message(STATUS "Architecture: ARM64")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "arm")
    set(HUSHELL_ARCH_ARM TRUE)
    add_compile_definitions(HUSHELL_ARCH_ARM)
    message(STATUS "Architecture: ARM")
else()
    message(WARNING "Unknown architecture: ${CMAKE_SYSTEM_PROCESSOR}")
endif()

# ==================== Linux平台特定设置 ====================

if(HUSHELL_PLATFORM_LINUX)
    # 查找Linux特定库
    find_package(PkgConfig REQUIRED)
    
    # 检查systemd支持
    pkg_check_modules(SYSTEMD systemd)
    if(SYSTEMD_FOUND)
        set(HUSHELL_HAS_SYSTEMD TRUE)
        add_compile_definitions(HUSHELL_HAS_SYSTEMD)
        message(STATUS "systemd support enabled")
    endif()
    
    # 检查libunwind（用于栈回溯）
    find_library(UNWIND_LIBRARY unwind)
    if(UNWIND_LIBRARY)
        set(HUSHELL_HAS_UNWIND TRUE)
        add_compile_definitions(HUSHELL_HAS_UNWIND)
        set(PLATFORM_LIBS ${PLATFORM_LIBS} ${UNWIND_LIBRARY})
        message(STATUS "libunwind found: ${UNWIND_LIBRARY}")
    endif()
    
    # 检查NUMA支持
    find_library(NUMA_LIBRARY numa)
    if(NUMA_LIBRARY)
        set(HUSHELL_HAS_NUMA TRUE)
        add_compile_definitions(HUSHELL_HAS_NUMA)
        set(PLATFORM_LIBS ${PLATFORM_LIBS} ${NUMA_LIBRARY})
        message(STATUS "NUMA support enabled")
    endif()
    
    # 检查epoll支持
    include(CheckSymbolExists)
    check_symbol_exists(epoll_create "sys/epoll.h" HUSHELL_HAS_EPOLL)
    if(HUSHELL_HAS_EPOLL)
        add_compile_definitions(HUSHELL_HAS_EPOLL)
        message(STATUS "epoll support detected")
    endif()
    
    # Linux基础库
    set(PLATFORM_LIBS ${PLATFORM_LIBS} pthread dl rt)
    
    # Linux特定优化标志
    set(LINUX_OPTIMIZATION_FLAGS "-fuse-ld=gold -flto=auto")
    
endif()

# ==================== Windows平台特定设置 ====================

if(HUSHELL_PLATFORM_WINDOWS)
    # Windows SDK检测
    if(CMAKE_VS_WINDOWS_TARGET_PLATFORM_VERSION)
        message(STATUS "Windows SDK version: ${CMAKE_VS_WINDOWS_TARGET_PLATFORM_VERSION}")
    endif()
    
    # 检查DirectML支持（AI加速）
    find_path(DIRECTML_INCLUDE_DIR DirectML.h
        PATHS "C:/Program Files (x86)/Windows Kits/10/Include/*/um"
        "C:/Program Files/Windows Kits/10/Include/*/um"
    )
    if(DIRECTML_INCLUDE_DIR)
        set(HUSHELL_HAS_DIRECTML TRUE)
        add_compile_definitions(HUSHELL_HAS_DIRECTML)
        message(STATUS "DirectML support detected")
    endif()
    
    # Windows基础库
    set(PLATFORM_LIBS ${PLATFORM_LIBS} ws2_32 winmm kernel32 user32 advapi32)
    
    # Windows特定编译选项
    add_compile_definitions(
        WIN32_LEAN_AND_MEAN
        NOMINMAX
        _WIN32_WINNT=0x0A00  # Windows 10+
        UNICODE
        _UNICODE
    )
    
    # Windows特定优化
    set(WINDOWS_OPTIMIZATION_FLAGS "/GL /Gy /Gw")
    
endif()

# ==================== macOS平台特定设置 ====================

if(HUSHELL_PLATFORM_MACOS)
    # 检查macOS版本
    execute_process(
        COMMAND sw_vers -productVersion
        OUTPUT_VARIABLE MACOS_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    message(STATUS "macOS version: ${MACOS_VERSION}")
    
    # 查找macOS特定框架
    find_library(FOUNDATION_FRAMEWORK Foundation)
    find_library(COREFOUNDATION_FRAMEWORK CoreFoundation)
    find_library(IOKIT_FRAMEWORK IOKit)
    
    if(FOUNDATION_FRAMEWORK)
        set(PLATFORM_LIBS ${PLATFORM_LIBS} ${FOUNDATION_FRAMEWORK})
        message(STATUS "Foundation framework found")
    endif()
    
    if(COREFOUNDATION_FRAMEWORK)
        set(PLATFORM_LIBS ${PLATFORM_LIBS} ${COREFOUNDATION_FRAMEWORK})
        message(STATUS "CoreFoundation framework found")
    endif()
    
    if(IOKIT_FRAMEWORK)
        set(PLATFORM_LIBS ${PLATFORM_LIBS} ${IOKIT_FRAMEWORK})
        message(STATUS "IOKit framework found")
    endif()
    
    # 检查Metal支持（GPU计算）
    find_library(METAL_FRAMEWORK Metal)
    if(METAL_FRAMEWORK)
        set(HUSHELL_HAS_METAL TRUE)
        add_compile_definitions(HUSHELL_HAS_METAL)
        set(PLATFORM_LIBS ${PLATFORM_LIBS} ${METAL_FRAMEWORK})
        message(STATUS "Metal framework found")
    endif()
    
    # 检查CoreML支持
    find_library(COREML_FRAMEWORK CoreML)
    if(COREML_FRAMEWORK)
        set(HUSHELL_HAS_COREML TRUE)
        add_compile_definitions(HUSHELL_HAS_COREML)
        set(PLATFORM_LIBS ${PLATFORM_LIBS} ${COREML_FRAMEWORK})
        message(STATUS "CoreML framework found")
    endif()
    
    # Grand Central Dispatch（已内置在系统中）
    set(HUSHELL_HAS_GCD TRUE)
    add_compile_definitions(HUSHELL_HAS_GCD)
    
    # macOS特定优化
    set(MACOS_OPTIMIZATION_FLAGS "-flto -fvisibility=hidden")
    
endif()

# ==================== 编译器特定优化 ====================

# GCC优化
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(COMPILER_OPTIMIZATION_FLAGS 
        "-O3 -march=native -mtune=native -ffast-math"
        "-fno-semantic-interposition -fdevirtualize-at-ltrans"
    )
    if(HUSHELL_PLATFORM_LINUX)
        set(COMPILER_OPTIMIZATION_FLAGS ${COMPILER_OPTIMIZATION_FLAGS} ${LINUX_OPTIMIZATION_FLAGS})
    endif()
    
# Clang优化
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    set(COMPILER_OPTIMIZATION_FLAGS 
        "-O3 -march=native -mtune=native -ffast-math"
        "-fvectorize -fslp-vectorize"
    )
    if(HUSHELL_PLATFORM_MACOS)
        set(COMPILER_OPTIMIZATION_FLAGS ${COMPILER_OPTIMIZATION_FLAGS} ${MACOS_OPTIMIZATION_FLAGS})
    endif()
    
# MSVC优化
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    set(COMPILER_OPTIMIZATION_FLAGS 
        "/O2 /Ob2 /Oi /Ot /arch:AVX2"
        "/fp:fast /GS- /Gy"
    )
    if(HUSHELL_PLATFORM_WINDOWS)
        set(COMPILER_OPTIMIZATION_FLAGS ${COMPILER_OPTIMIZATION_FLAGS} ${WINDOWS_OPTIMIZATION_FLAGS})
    endif()
endif()

# ==================== 功能特性检测 ====================

# 检查线程支持
find_package(Threads REQUIRED)
set(PLATFORM_LIBS ${PLATFORM_LIBS} Threads::Threads)

# 检查原子操作支持
include(CheckCXXSourceCompiles)
check_cxx_source_compiles("
    #include <atomic>
    int main() {
        std::atomic<int> x{0};
        return x.load();
    }
" HUSHELL_HAS_ATOMIC)

if(HUSHELL_HAS_ATOMIC)
    add_compile_definitions(HUSHELL_HAS_ATOMIC)
else()
    message(WARNING "Atomic operations not supported")
endif()

# 检查协程支持
check_cxx_source_compiles("
    #include <coroutine>
    #include <future>
    
    std::future<int> test_coroutine() {
        co_return 42;
    }
    
    int main() {
        return 0;
    }
" HUSHELL_HAS_COROUTINES)

if(HUSHELL_HAS_COROUTINES)
    add_compile_definitions(HUSHELL_HAS_COROUTINES)
    message(STATUS "C++20 coroutines support detected")
else()
    message(WARNING "C++20 coroutines not supported")
endif()

# ==================== 导出平台信息 ====================

# 创建平台配置头文件
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/platform_config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/include/nex/platform_config.h"
    @ONLY
)

# 设置全局变量供其他CMake文件使用
set(HUSHELL_PLATFORM_LIBS ${PLATFORM_LIBS} CACHE INTERNAL "Platform-specific libraries")
set(HUSHELL_OPTIMIZATION_FLAGS ${COMPILER_OPTIMIZATION_FLAGS} CACHE INTERNAL "Platform-specific optimization flags")

# 创建平台配置摘要
message(STATUS "=== Platform Configuration Summary ===")
message(STATUS "Platform: ${PLATFORM_NAME}")
message(STATUS "Architecture: ${CMAKE_SYSTEM_PROCESSOR}")
message(STATUS "Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Platform libraries: ${PLATFORM_LIBS}")
message(STATUS "Optimization flags: ${COMPILER_OPTIMIZATION_FLAGS}")
message(STATUS "=======================================")