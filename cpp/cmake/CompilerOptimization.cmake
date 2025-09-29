# CompilerOptimization.cmake - 编译器特定优化配置
# 基于设计文档实现针对不同编译器的现代C++20优化策略

cmake_minimum_required(VERSION 3.20)

# ==================== C++20标准和特性检测 ====================

# 确保C++20支持
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 检查编译器版本和C++20支持
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "10.0")
        message(FATAL_ERROR "GCC 10.0+ required for C++20 support. Current: ${CMAKE_CXX_COMPILER_VERSION}")
    endif()
    message(STATUS "Using GCC ${CMAKE_CXX_COMPILER_VERSION} with C++20 support")
    
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "12.0")
        message(FATAL_ERROR "Clang 12.0+ required for C++20 support. Current: ${CMAKE_CXX_COMPILER_VERSION}")
    endif()
    message(STATUS "Using Clang ${CMAKE_CXX_COMPILER_VERSION} with C++20 support")
    
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "19.29")
        message(FATAL_ERROR "MSVC 19.29+ (VS 2019 16.10) required for C++20 support. Current: ${CMAKE_CXX_COMPILER_VERSION}")
    endif()
    message(STATUS "Using MSVC ${CMAKE_CXX_COMPILER_VERSION} with C++20 support")
    
else()
    message(WARNING "Unknown compiler: ${CMAKE_CXX_COMPILER_ID}. C++20 support not guaranteed.")
endif()

# ==================== GCC特定优化 ====================

function(configure_gcc_optimization target)
    target_compile_options(${target} PRIVATE
        # C++20特性启用
        -fcoroutines
        -fconcepts
        -fconcepts-diagnostics-depth=2
        
        # 基础优化
        -O3
        -march=native
        -mtune=native
        -ffast-math
        -funroll-loops
        -fvectorize
        
        # 链接时优化
        -flto=auto
        -fno-semantic-interposition
        -fdevirtualize-at-ltrans
        
        # 内存和缓存优化
        -fdata-sections
        -ffunction-sections
        -falign-functions=32
        -falign-loops=32
        
        # 现代C++优化
        -fno-rtti  # 如果不需要RTTI
        -fvisibility=hidden
        -fvisibility-inlines-hidden
        
        # 安全优化
        -fstack-protector-strong
        -D_FORTIFY_SOURCE=2
        
        # 警告设置
        -Wall
        -Wextra
        -Wpedantic
        -Wconversion
        -Wsign-conversion
        -Wunused
        -Wformat=2
        -Wformat-security
    )
    
    # 链接器优化
    target_link_options(${target} PRIVATE
        -Wl,--gc-sections
        -Wl,--strip-all
        -Wl,-O3
        -flto=auto
    )
    
    # Debug模式特定设置
    target_compile_options(${target} PRIVATE
        $<$<CONFIG:Debug>:-g3 -O0 -DDEBUG -fno-omit-frame-pointer>
        $<$<CONFIG:Debug>:-fsanitize=address -fsanitize=undefined>
    )
    
    target_link_options(${target} PRIVATE
        $<$<CONFIG:Debug>:-fsanitize=address -fsanitize=undefined>
    )
    
    message(STATUS "Applied GCC optimization configuration to ${target}")
endfunction()

# ==================== Clang特定优化 ====================

function(configure_clang_optimization target)
    target_compile_options(${target} PRIVATE
        # C++20特性启用
        -fcoroutines-ts
        
        # 基础优化
        -O3
        -march=native
        -mtune=native
        -ffast-math
        -funroll-loops
        
        # Clang特定向量化
        -fvectorize
        -fslp-vectorize
        -fforce-enable-int128
        
        # 链接时优化
        -flto=thin
        
        # 内存优化
        -fdata-sections
        -ffunction-sections
        
        # 现代C++优化
        -fvisibility=hidden
        -fvisibility-inlines-hidden
        
        # 安全设置
        -fstack-protector-strong
        -D_FORTIFY_SOURCE=2
        
        # 警告设置
        -Wall
        -Wextra
        -Wpedantic
        -Wconversion
        -Wsign-conversion
        -Wunused
        -Wformat=2
        -Wthread-safety
    )
    
    # macOS特定设置
    if(APPLE)
        target_compile_options(${target} PRIVATE
            -stdlib=libc++
            -mmacosx-version-min=10.15
        )
    endif()
    
    # 链接器优化
    target_link_options(${target} PRIVATE
        -Wl,-dead_strip  # macOS
        $<$<NOT:$<PLATFORM_ID:Darwin>>:-Wl,--gc-sections>  # Linux
        -flto=thin
    )
    
    # Debug模式特定设置
    target_compile_options(${target} PRIVATE
        $<$<CONFIG:Debug>:-g3 -O0 -DDEBUG -fno-omit-frame-pointer>
        $<$<CONFIG:Debug>:-fsanitize=address -fsanitize=undefined>
    )
    
    target_link_options(${target} PRIVATE
        $<$<CONFIG:Debug>:-fsanitize=address -fsanitize=undefined>
    )
    
    message(STATUS "Applied Clang optimization configuration to ${target}")
endfunction()

# ==================== MSVC特定优化 ====================

function(configure_msvc_optimization target)
    target_compile_options(${target} PRIVATE
        # C++20支持
        /std:c++20
        /Zc:__cplusplus
        /permissive-
        
        # 基础优化
        /O2
        /Ob2  # 内联优化
        /Oi   # 内置函数
        /Ot   # 优化速度
        /arch:AVX2
        
        # 浮点优化
        /fp:fast
        /fp:except-
        
        # 全程序优化
        /GL
        /Gy   # 函数级链接
        /Gw   # 全局数据优化
        
        # 安全优化
        /GS   # 缓冲区安全检查
        /guard:cf  # 控制流保护
        
        # 代码生成
        /favor:INTEL64
        /Zc:inline
        /Zc:throwingNew
        
        # 警告设置
        /W4
        /wd4251  # 禁用DLL接口警告
        /wd4275  # 禁用DLL基类警告
        
        # 编译时优化
        /MP   # 多处理器编译
        /bigobj  # 大对象文件
    )
    
    # 链接器优化
    target_link_options(${target} PRIVATE
        /LTCG     # 链接时代码生成
        /OPT:REF  # 消除未引用函数
        /OPT:ICF  # 合并相同函数
        /INCREMENTAL:NO
    )
    
    # Debug模式特定设置
    target_compile_options(${target} PRIVATE
        $<$<CONFIG:Debug>:/Od /Zi /DDEBUG /RTC1>
        $<$<CONFIG:Debug>:/fsanitize=address>
    )
    
    # 预定义宏
    target_compile_definitions(${target} PRIVATE
        WIN32_LEAN_AND_MEAN
        NOMINMAX
        _WIN32_WINNT=0x0A00
        UNICODE
        _UNICODE
        _CRT_SECURE_NO_WARNINGS
        _SCL_SECURE_NO_WARNINGS
    )
    
    message(STATUS "Applied MSVC optimization configuration to ${target}")
endfunction()

# ==================== 通用优化函数 ====================

function(apply_compiler_optimizations target)
    # 检查目标是否存在
    if(NOT TARGET ${target})
        message(FATAL_ERROR "Target ${target} does not exist")
    endif()
    
    # 根据编译器应用相应优化
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        configure_gcc_optimization(${target})
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        configure_clang_optimization(${target})
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        configure_msvc_optimization(${target})
    else()
        message(WARNING "No specific optimizations configured for compiler: ${CMAKE_CXX_COMPILER_ID}")
    endif()
    
    # 通用C++20特性
    target_compile_features(${target} PUBLIC cxx_std_20)
    
    # 通用编译定义
    target_compile_definitions(${target} PRIVATE
        $<$<CONFIG:Debug>:HUSHELL_DEBUG_BUILD>
        $<$<CONFIG:Release>:HUSHELL_RELEASE_BUILD>
        $<$<CONFIG:RelWithDebInfo>:HUSHELL_RELWITHDEBINFO_BUILD>
        $<$<CONFIG:MinSizeRel>:HUSHELL_MINSIZEREL_BUILD>
    )
endfunction()

# ==================== 性能剖析支持 ====================

function(enable_profiling target)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        target_compile_options(${target} PRIVATE -pg -fno-omit-frame-pointer)
        target_link_options(${target} PRIVATE -pg)
        message(STATUS "Profiling enabled for ${target}")
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        # MSVC可以使用PDB文件进行性能分析
        target_compile_options(${target} PRIVATE /Zi)
        target_link_options(${target} PRIVATE /DEBUG)
        message(STATUS "Debug symbols enabled for profiling: ${target}")
    endif()
endfunction()

# ==================== 代码覆盖率支持 ====================

function(enable_coverage target)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        target_compile_options(${target} PRIVATE 
            --coverage 
            -fprofile-arcs 
            -ftest-coverage
            -fno-inline
            -fno-inline-small-functions
            -fno-default-inline
        )
        target_link_options(${target} PRIVATE --coverage)
        
        if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
            target_link_libraries(${target} PRIVATE gcov)
        endif()
        
        message(STATUS "Code coverage enabled for ${target}")
    else()
        message(WARNING "Code coverage not supported for compiler: ${CMAKE_CXX_COMPILER_ID}")
    endif()
endfunction()

# ==================== 检测器支持 ====================

function(enable_sanitizers target)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        target_compile_options(${target} PRIVATE
            -fsanitize=address
            -fsanitize=undefined
            -fsanitize=leak
            -fno-sanitize-recover=all
            -fno-omit-frame-pointer
        )
        target_link_options(${target} PRIVATE
            -fsanitize=address
            -fsanitize=undefined
            -fsanitize=leak
        )
        message(STATUS "Sanitizers enabled for ${target}")
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        target_compile_options(${target} PRIVATE /fsanitize=address)
        message(STATUS "AddressSanitizer enabled for ${target}")
    endif()
endfunction()

# 输出编译器配置摘要
message(STATUS "=== Compiler Configuration Summary ===")
message(STATUS "Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "C++ Standard: C++${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Target Architecture: ${CMAKE_SYSTEM_PROCESSOR}")
message(STATUS "========================================")