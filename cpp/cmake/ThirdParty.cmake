# ThirdParty.cmake - 第三方依赖管理
# 基于设计文档实现统一的第三方库管理和版本控制

cmake_minimum_required(VERSION 3.20)

# ==================== 包管理器配置 ====================

# 优先使用vcpkg（如果存在）
if(DEFINED ENV{VCPKG_ROOT})
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake" CACHE STRING "")
    message(STATUS "Using vcpkg from: $ENV{VCPKG_ROOT}")
    set(HUSHELL_USING_VCPKG TRUE)
endif()

# 检查Conan支持
if(EXISTS "${CMAKE_CURRENT_BINARY_DIR}/conan_toolchain.cmake")
    include("${CMAKE_CURRENT_BINARY_DIR}/conan_toolchain.cmake")
    message(STATUS "Using Conan package manager")
    set(HUSHELL_USING_CONAN TRUE)
endif()

# ==================== 核心依赖查找 ====================

# gRPC和Protobuf - 通信层核心
find_package(gRPC CONFIG QUIET)
find_package(Protobuf CONFIG QUIET)

if(gRPC_FOUND AND Protobuf_FOUND)
    set(HUSHELL_ENABLE_GRPC TRUE)
    message(STATUS "✓ gRPC found: ${gRPC_VERSION}")
    message(STATUS "✓ Protobuf found: ${Protobuf_VERSION}")
    
    # 创建方便的目标别名
    if(TARGET gRPC::grpc++)
        add_library(hushell::grpc ALIAS gRPC::grpc++)
    endif()
    if(TARGET protobuf::libprotobuf)
        add_library(hushell::protobuf ALIAS protobuf::libprotobuf)
    endif()
else()
    set(HUSHELL_ENABLE_GRPC FALSE)
    message(WARNING "✗ gRPC/Protobuf not found - RPC features disabled")
endif()

# Google Test - 测试框架
find_package(GTest CONFIG QUIET)
if(GTest_FOUND)
    set(HUSHELL_ENABLE_TESTING TRUE)
    message(STATUS "✓ Google Test found: ${GTest_VERSION}")
    
    # 创建测试目标别名
    if(TARGET GTest::gtest)
        add_library(hushell::gtest ALIAS GTest::gtest)
    endif()
    if(TARGET GTest::gtest_main)
        add_library(hushell::gtest_main ALIAS GTest::gtest_main)
    endif()
    if(TARGET GTest::gmock)
        add_library(hushell::gmock ALIAS GTest::gmock)
    endif()
else()
    set(HUSHELL_ENABLE_TESTING FALSE)
    message(WARNING "✗ Google Test not found - unit tests disabled")
endif()

# Google Benchmark - 性能测试
find_package(benchmark CONFIG QUIET)
if(benchmark_FOUND)
    set(HUSHELL_ENABLE_BENCHMARKS TRUE)
    message(STATUS "✓ Google Benchmark found")
    add_library(hushell::benchmark ALIAS benchmark::benchmark)
else()
    set(HUSHELL_ENABLE_BENCHMARKS FALSE)
    message(STATUS "○ Google Benchmark not found - benchmarks disabled")
endif()

# ==================== 现代C++库 ====================

# fmt - 现代字符串格式化
find_package(fmt CONFIG QUIET)
if(fmt_FOUND)
    set(HUSHELL_HAS_FMT TRUE)
    message(STATUS "✓ fmt found: ${fmt_VERSION}")
    add_library(hushell::fmt ALIAS fmt::fmt)
else()
    set(HUSHELL_HAS_FMT FALSE)
    message(STATUS "○ fmt not found - using std::format fallback")
endif()

# spdlog - 高性能日志库
find_package(spdlog CONFIG QUIET)
if(spdlog_FOUND)
    set(HUSHELL_HAS_SPDLOG TRUE)
    message(STATUS "✓ spdlog found: ${spdlog_VERSION}")
    add_library(hushell::spdlog ALIAS spdlog::spdlog)
else()
    set(HUSHELL_HAS_SPDLOG FALSE)
    message(STATUS "○ spdlog not found - using basic logging")
endif()

# nlohmann/json - JSON处理
find_package(nlohmann_json CONFIG QUIET)
if(nlohmann_json_FOUND)
    set(HUSHELL_HAS_JSON TRUE)
    message(STATUS "✓ nlohmann_json found: ${nlohmann_json_VERSION}")
    add_library(hushell::json ALIAS nlohmann_json::nlohmann_json)
else()
    set(HUSHELL_HAS_JSON FALSE)
    message(STATUS "○ nlohmann_json not found")
endif()

# ==================== 系统库 ====================

# 线程支持（必需）
find_package(Threads REQUIRED)
message(STATUS "✓ Threads support found")

# OpenSSL - 加密和安全
find_package(OpenSSL QUIET)
if(OpenSSL_FOUND)
    set(HUSHELL_HAS_OPENSSL TRUE)
    message(STATUS "✓ OpenSSL found: ${OPENSSL_VERSION}")
    add_library(hushell::openssl ALIAS OpenSSL::SSL)
    add_library(hushell::crypto ALIAS OpenSSL::Crypto)
else()
    set(HUSHELL_HAS_OPENSSL FALSE)
    message(STATUS "○ OpenSSL not found - encryption features limited")
endif()

# CURL - HTTP客户端
find_package(CURL QUIET)
if(CURL_FOUND)
    set(HUSHELL_HAS_CURL TRUE)
    message(STATUS "✓ CURL found: ${CURL_VERSION_STRING}")
    add_library(hushell::curl ALIAS CURL::libcurl)
else()
    set(HUSHELL_HAS_CURL FALSE)
    message(STATUS "○ CURL not found - HTTP client features disabled")
endif()

# ==================== AI/ML库 ====================

# CUDA - GPU计算（可选）
find_package(CUDAToolkit QUIET)
if(CUDAToolkit_FOUND)
    enable_language(CUDA)
    set(HUSHELL_HAS_CUDA TRUE)
    set(CMAKE_CUDA_STANDARD 20)
    set(CMAKE_CUDA_STANDARD_REQUIRED ON)
    message(STATUS "✓ CUDA found: ${CUDAToolkit_VERSION}")
    
    # 创建CUDA目标别名
    add_library(hushell::cuda_runtime ALIAS CUDA::cudart)
    add_library(hushell::cublas ALIAS CUDA::cublas)
    add_library(hushell::curand ALIAS CUDA::curand)
    
    # 检查compute capability
    if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
        set(CMAKE_CUDA_ARCHITECTURES "70;75;80;86" CACHE STRING "CUDA architectures")
    endif()
    
else()
    set(HUSHELL_HAS_CUDA FALSE)
    message(STATUS "○ CUDA not found - GPU acceleration disabled")
endif()

# OpenCL - 跨平台并行计算（可选）
find_package(OpenCL QUIET)
if(OpenCL_FOUND)
    set(HUSHELL_HAS_OPENCL TRUE)
    message(STATUS "✓ OpenCL found: ${OpenCL_VERSION_STRING}")
    add_library(hushell::opencl ALIAS OpenCL::OpenCL)
else()
    set(HUSHELL_HAS_OPENCL FALSE)
    message(STATUS "○ OpenCL not found")
endif()

# ==================== 数据库支持 ====================

# SQLite - 轻量级数据库
find_package(SQLite3 QUIET)
if(SQLite3_FOUND)
    set(HUSHELL_HAS_SQLITE TRUE)
    message(STATUS "✓ SQLite3 found: ${SQLite3_VERSION}")
    add_library(hushell::sqlite3 ALIAS SQLite::SQLite3)
else()
    set(HUSHELL_HAS_SQLITE FALSE)
    message(STATUS "○ SQLite3 not found")
endif()

# Redis C++ client (可选)
find_package(redis++ CONFIG QUIET)
if(redis++_FOUND)
    set(HUSHELL_HAS_REDIS TRUE)
    message(STATUS "✓ redis++ found")
    add_library(hushell::redis ALIAS redis++::redis++)
else()
    set(HUSHELL_HAS_REDIS FALSE)
    message(STATUS "○ redis++ not found")
endif()

# ==================== 特殊配置和功能检测 ====================

# 检查是否支持内存映射文件
include(CheckIncludeFile)
check_include_file("sys/mman.h" HUSHELL_HAS_MMAP)
if(WIN32)
    set(HUSHELL_HAS_WINDOWS_MMAP TRUE)
endif()

# 检查大页面支持
if(HUSHELL_PLATFORM_LINUX)
    find_path(HUGEPAGE_PATH huge_pages PATHS /proc/sys/vm NO_DEFAULT_PATH)
    if(HUGEPAGE_PATH)
        set(HUSHELL_HAS_HUGEPAGES TRUE)
        message(STATUS "✓ Huge pages support detected")
    endif()
endif()

# ==================== 自动下载缺失依赖 ====================

# 创建FetchContent配置用于自动下载关键依赖
include(FetchContent)

# 如果没有找到关键库，尝试自动下载
if(NOT HUSHELL_HAS_JSON)
    message(STATUS "Attempting to fetch nlohmann_json...")
    FetchContent_Declare(
        nlohmann_json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG v3.11.2
        GIT_SHALLOW TRUE
    )
    FetchContent_MakeAvailable(nlohmann_json)
    set(HUSHELL_HAS_JSON TRUE)
    add_library(hushell::json ALIAS nlohmann_json)
    message(STATUS "✓ nlohmann_json fetched and configured")
endif()

# ==================== 编译定义和配置 ====================

function(configure_target_dependencies target)
    # 必需依赖
    target_link_libraries(${target} PRIVATE Threads::Threads)
    
    # 可选依赖 - 根据可用性链接
    if(HUSHELL_ENABLE_GRPC)
        target_link_libraries(${target} PRIVATE hushell::grpc hushell::protobuf)
        target_compile_definitions(${target} PRIVATE HUSHELL_ENABLE_GRPC)
    endif()
    
    if(HUSHELL_HAS_FMT)
        target_link_libraries(${target} PRIVATE hushell::fmt)
        target_compile_definitions(${target} PRIVATE HUSHELL_HAS_FMT)
    endif()
    
    if(HUSHELL_HAS_SPDLOG)
        target_link_libraries(${target} PRIVATE hushell::spdlog)
        target_compile_definitions(${target} PRIVATE HUSHELL_HAS_SPDLOG)
    endif()
    
    if(HUSHELL_HAS_JSON)
        target_link_libraries(${target} PRIVATE hushell::json)
        target_compile_definitions(${target} PRIVATE HUSHELL_HAS_JSON)
    endif()
    
    if(HUSHELL_HAS_OPENSSL)
        target_link_libraries(${target} PRIVATE hushell::openssl hushell::crypto)
        target_compile_definitions(${target} PRIVATE HUSHELL_HAS_OPENSSL)
    endif()
    
    if(HUSHELL_HAS_CURL)
        target_link_libraries(${target} PRIVATE hushell::curl)
        target_compile_definitions(${target} PRIVATE HUSHELL_HAS_CURL)
    endif()
    
    if(HUSHELL_HAS_CUDA)
        target_link_libraries(${target} PRIVATE hushell::cuda_runtime)
        target_compile_definitions(${target} PRIVATE HUSHELL_HAS_CUDA)
        set_property(TARGET ${target} PROPERTY CUDA_SEPARABLE_COMPILATION ON)
    endif()
    
    if(HUSHELL_HAS_SQLITE)
        target_link_libraries(${target} PRIVATE hushell::sqlite3)
        target_compile_definitions(${target} PRIVATE HUSHELL_HAS_SQLITE)
    endif()
    
    message(STATUS "Configured dependencies for target: ${target}")
endfunction()

# ==================== 依赖摘要 ====================

message(STATUS "=== Third-Party Dependencies Summary ===")
message(STATUS "Package Manager: ${HUSHELL_USING_VCPKG:+vcpkg}${HUSHELL_USING_CONAN:+conan}${HUSHELL_USING_VCPKG:+${HUSHELL_USING_CONAN:+}}${HUSHELL_USING_VCPKG:+${HUSHELL_USING_CONAN:+}}${HUSHELL_USING_VCPKG}${HUSHELL_USING_CONAN}${HUSHELL_USING_VCPKG:+${HUSHELL_USING_CONAN:+}}system")
message(STATUS "gRPC/Protobuf: ${HUSHELL_ENABLE_GRPC:+✓ enabled}${HUSHELL_ENABLE_GRPC:+}${HUSHELL_ENABLE_GRPC}${HUSHELL_ENABLE_GRPC:+}✗ disabled")
message(STATUS "Google Test: ${HUSHELL_ENABLE_TESTING:+✓ enabled}${HUSHELL_ENABLE_TESTING:+}${HUSHELL_ENABLE_TESTING}${HUSHELL_ENABLE_TESTING:+}✗ disabled")
message(STATUS "Benchmarks: ${HUSHELL_ENABLE_BENCHMARKS:+✓ enabled}${HUSHELL_ENABLE_BENCHMARKS:+}${HUSHELL_ENABLE_BENCHMARKS}${HUSHELL_ENABLE_BENCHMARKS:+}○ disabled")
message(STATUS "fmt: ${HUSHELL_HAS_FMT:+✓ available}${HUSHELL_HAS_FMT:+}${HUSHELL_HAS_FMT}${HUSHELL_HAS_FMT:+}○ fallback")
message(STATUS "spdlog: ${HUSHELL_HAS_SPDLOG:+✓ available}${HUSHELL_HAS_SPDLOG:+}${HUSHELL_HAS_SPDLOG}${HUSHELL_HAS_SPDLOG:+}○ basic logging")
message(STATUS "JSON: ${HUSHELL_HAS_JSON:+✓ available}${HUSHELL_HAS_JSON:+}${HUSHELL_HAS_JSON}${HUSHELL_HAS_JSON:+}✗ missing")
message(STATUS "OpenSSL: ${HUSHELL_HAS_OPENSSL:+✓ available}${HUSHELL_HAS_OPENSSL:+}${HUSHELL_HAS_OPENSSL}${HUSHELL_HAS_OPENSSL:+}○ limited encryption")
message(STATUS "CUDA: ${HUSHELL_HAS_CUDA:+✓ available}${HUSHELL_HAS_CUDA:+}${HUSHELL_HAS_CUDA}${HUSHELL_HAS_CUDA:+}○ CPU only")
message(STATUS "SQLite: ${HUSHELL_HAS_SQLITE:+✓ available}${HUSHELL_HAS_SQLITE:+}${HUSHELL_HAS_SQLITE}${HUSHELL_HAS_SQLITE:+}○ not available")
message(STATUS "==========================================")