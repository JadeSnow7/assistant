cmake_minimum_required(VERSION 3.20)
project(nex_ai_assistant VERSION 2.0.0 LANGUAGES CXX)

# 设置模块路径
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

# 设置C++标准
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 引入新的模块化配置
include(PlatformDetection)
include(CompilerOptimization)
include(ThirdParty)

# 启用C++20特性
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "10.0")
        message(FATAL_ERROR "GCC 10.0 or higher is required for C++20 support")
    endif()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fcoroutines -fconcepts")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "12.0")
        message(FATAL_ERROR "Clang 12.0 or higher is required for C++20 support")
    endif()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++ -fcoroutines-ts")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    if(CMAKE_CXX_COMPILER_VERSION VERSION_LESS "19.29")
        message(FATAL_ERROR "MSVC 19.29 or higher is required for C++20 support")
    endif()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /std:c++20")
endif()

# 编译选项
if(NOT WIN32)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -g -O0 -DDEBUG -fsanitize=address")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -DNDEBUG -march=native -mtune=native")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /W4")
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} /Od /Zi /DDEBUG")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /O2 /DNDEBUG")
endif()

# 查找依赖包
find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)

# gRPC和Protobuf（可选）
find_package(gRPC QUIET)
find_package(Protobuf QUIET)
if(NOT gRPC_FOUND OR NOT Protobuf_FOUND)
    message(STATUS "gRPC or Protobuf not found, some features will be disabled")
    set(ENABLE_GRPC_FEATURES OFF)
else()
    message(STATUS "gRPC and Protobuf found, enabling gRPC features")
    set(ENABLE_GRPC_FEATURES ON)
endif()

# GTest（可选）
find_package(GTest QUIET)
if(NOT GTest_FOUND)
    message(STATUS "GTest not found, unit tests will be disabled")
    set(ENABLE_TESTING OFF)
else()
    message(STATUS "GTest found, enabling unit tests")
    set(ENABLE_TESTING ON)
endif()

# 查找现代C++库
find_package(fmt QUIET)
if(NOT fmt_FOUND)
    message(STATUS "fmt not found, will use system headers")
endif()

find_package(spdlog QUIET)
if(NOT spdlog_FOUND)
    message(STATUS "spdlog not found, will use basic logging")
endif()

# 查找CUDA（可选）
find_package(CUDA QUIET)
if(CUDA_FOUND)
    enable_language(CUDA)
    add_definitions(-DENABLE_CUDA)
    message(STATUS "CUDA found, enabling GPU acceleration")
else()
    message(STATUS "CUDA not found, GPU acceleration disabled")
endif()

# 包含目录 - 使用新的模块化结构
include_directories(include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${CMAKE_CURRENT_BINARY_DIR}/include)  # 生成的头文件

# 新的模块化源文件结构

# 平台抽象层
set(PLATFORM_SOURCES
    src/core/platform/platform_detector.cpp
    src/core/platform/unix_platform_adapter.cpp
    src/core/platform/platform_factory.cpp
)

# Shell系统
set(SHELL_SOURCES
    src/core/shell/shell_command.cpp
    # src/core/shell/shell_executor.cpp  # 待实现
)

# 推理引擎
set(INFERENCE_SOURCES
    # src/core/inference/model_engine.cpp  # 待实现
    # src/core/inference/local_model_provider.cpp  # 待实现
    # src/core/inference/cloud_model_provider.cpp  # 待实现
)

# 系统管理
set(SYSTEM_SOURCES
    # src/core/system/system_manager.cpp  # 待实现
)

# 插件系统
set(PLUGIN_SOURCES
    # src/core/plugin/plugin_manager.cpp  # 待实现
)

# gRPC通信
set(GRPC_SOURCES
    # src/core/grpc/grpc_server.cpp  # 待实现
)

# 内存管理
set(MEMORY_SOURCES
    # src/core/memory/memory_allocator.cpp  # 待实现
)

# 传统源文件（向后兼容）
set(LEGACY_SOURCES
    src/model_engine.cpp
    src/sys_manager.cpp
    src/plugin_loader.cpp
    src/grpc_server.cpp
    src/common.cpp
    src/performance_analyzer.cpp
    src/memory_optimizer.cpp
    src/gpu_engine.cpp
)

# 所有源文件
set(ALL_SOURCES 
    ${PLATFORM_SOURCES} 
    ${SHELL_SOURCES} 
    ${INFERENCE_SOURCES}
    ${SYSTEM_SOURCES} 
    ${PLUGIN_SOURCES} 
    ${GRPC_SOURCES}
    ${MEMORY_SOURCES}
    ${LEGACY_SOURCES}
)

# 新的模块化头文件结构

# 平台抽象层头文件
set(PLATFORM_HEADERS
    include/nex/platform/platform_detector.hpp
    include/nex/platform/platform_adapter.hpp
    include/nex/platform/unix_platform_adapter.hpp
    include/nex/platform/platform_factory.hpp
)

# Shell系统头文件
set(SHELL_HEADERS
    include/nex/shell/shell_command.hpp
    include/nex/shell/shell_executor.hpp
)

# 核心概念头文件
set(CONCEPTS_HEADERS
    include/nex/concepts/core_concepts.hpp
)

# 推理引擎头文件
set(INFERENCE_HEADERS
    include/nex/core/inference_types.hpp
    include/nex/core/model_engine.hpp
)

# 传统头文件（向后兼容）
set(LEGACY_HEADERS
    include/model_engine.hpp
    include/sys_manager.hpp
    include/plugin_loader.hpp
    include/grpc_server.hpp
    include/common.hpp
    include/performance_analyzer.hpp
    include/memory_optimizer.hpp
    include/gpu_engine.hpp
    include/async_scheduler.hpp
    include/model_cache.hpp
    include/benchmark_framework.hpp
    include/optimized_model_engine.hpp
)

# 所有头文件
set(ALL_HEADERS 
    ${PLATFORM_HEADERS} 
    ${SHELL_HEADERS} 
    ${CONCEPTS_HEADERS}
    ${INFERENCE_HEADERS}
    ${LEGACY_HEADERS}
)

# 创建模块化库 - 优化版本

# 平台抽象层库
add_library(nex_platform SHARED ${PLATFORM_SOURCES} ${PLATFORM_HEADERS})
set_target_properties(nex_platform PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)
# 应用优化配置
apply_compiler_optimizations(nex_platform)
configure_target_dependencies(nex_platform)
target_link_libraries(nex_platform PUBLIC ${HUSHELL_PLATFORM_LIBS})

# Shell系统库
add_library(nex_shell SHARED ${SHELL_SOURCES} ${SHELL_HEADERS})
set_target_properties(nex_shell PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)
apply_compiler_optimizations(nex_shell)
configure_target_dependencies(nex_shell)
target_link_libraries(nex_shell PUBLIC nex_platform)

# 推理引擎库
add_library(nex_inference SHARED ${INFERENCE_SOURCES} ${INFERENCE_HEADERS})
set_target_properties(nex_inference PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)
apply_compiler_optimizations(nex_inference)
configure_target_dependencies(nex_inference)

# 主核心库（整合所有模块）
add_library(ai_assistant_core SHARED ${ALL_SOURCES} ${ALL_HEADERS})
set_target_properties(ai_assistant_core PROPERTIES
    VERSION 2.0.0
    SOVERSION 2
    PUBLIC_HEADER "${ALL_HEADERS}"
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)

# 应用现代化优化配置
apply_compiler_optimizations(ai_assistant_core)
configure_target_dependencies(ai_assistant_core)

# 模块间依赖关系
target_link_libraries(ai_assistant_core PUBLIC 
    nex_platform 
    nex_shell
    nex_inference
    ${HUSHELL_PLATFORM_LIBS}
)

# 启用C++20特性
target_compile_features(ai_assistant_core PUBLIC cxx_std_20)
target_compile_features(nex_platform PUBLIC cxx_std_20)
target_compile_features(nex_shell PUBLIC cxx_std_20)
target_compile_features(nex_inference PUBLIC cxx_std_20)

# 链接库
target_link_libraries(ai_assistant_core
    PUBLIC
    Threads::Threads
    ${CMAKE_DL_LIBS}
)

# 条件性链接gRPC和Protobuf
if(ENABLE_GRPC_FEATURES)
    target_link_libraries(ai_assistant_core PUBLIC gRPC::grpc++ protobuf::libprotobuf)
    target_compile_definitions(ai_assistant_core PUBLIC ENABLE_GRPC_FEATURES)
endif()

# 为各个模块链接基础库
target_link_libraries(nex_platform
    PUBLIC
    Threads::Threads
    ${CMAKE_DL_LIBS}
)

target_link_libraries(nex_shell
    PUBLIC
    Threads::Threads
)

target_link_libraries(nex_inference
    PUBLIC
    Threads::Threads
)

# 链接现代C++库（如果可用）
if(fmt_FOUND)
    target_link_libraries(ai_assistant_core PUBLIC fmt::fmt)
    target_link_libraries(nex_platform PUBLIC fmt::fmt)
endif()

if(spdlog_FOUND)
    target_link_libraries(ai_assistant_core PUBLIC spdlog::spdlog)
    target_link_libraries(nex_platform PUBLIC spdlog::spdlog)
endif()

# 如果找到CUDA，链接CUDA库
if(CUDA_FOUND)
    target_link_libraries(ai_assistant_core
        PUBLIC
        ${CUDA_LIBRARIES}
        ${CUDA_CUBLAS_LIBRARIES}
    )
    target_include_directories(ai_assistant_core
        PUBLIC
        ${CUDA_INCLUDE_DIRS}
    )
endif()

# 可执行文件
add_executable(ai_assistant_server src/main.cpp)
apply_compiler_optimizations(ai_assistant_server)
configure_target_dependencies(ai_assistant_server)
target_link_libraries(ai_assistant_server ai_assistant_core)

# 性能测试可执行文件
if(HUSHELL_ENABLE_TESTING)
    add_executable(performance_tests
        tests/performance_integration_tests.cpp
    )
    apply_compiler_optimizations(performance_tests)
    configure_target_dependencies(performance_tests)
    target_link_libraries(performance_tests
        ai_assistant_core
        hushell::gtest
        hushell::gtest_main
    )
else()
    # 创建空的性能测试目标（向后兼容）
    add_custom_target(performance_tests
        COMMAND echo "Testing disabled - GTest not found"
        COMMENT "Testing disabled"
    )
endif()

# 安装配置
install(TARGETS 
    ai_assistant_core 
    ai_assistant_server
    nex_platform
    nex_shell
    nex_inference
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
    PUBLIC_HEADER DESTINATION include/nex
)

# 安装头文件目录结构
install(DIRECTORY include/nex/ DESTINATION include/nex
        FILES_MATCHING PATTERN "*.hpp")

# 测试
enable_testing()
add_test(NAME PerformanceIntegrationTests COMMAND performance_tests)

# 性能基准测试目标
if(ENABLE_TESTING)
    add_custom_target(benchmark
        COMMAND ./performance_tests --gtest_filter="*Benchmark*"
        DEPENDS performance_tests
        COMMENT "Running performance benchmarks"
    )

    # 压力测试目标
    add_custom_target(stress_test
        COMMAND ./performance_tests --gtest_filter="*Stress*"
        DEPENDS performance_tests
        COMMENT "Running stress tests"
    )

    # 完整测试套件
    add_custom_target(full_test_suite
        COMMAND ./performance_tests
        DEPENDS performance_tests
        COMMENT "Running full performance test suite"
    )
else()
    # 创建空的测试目标
    add_custom_target(benchmark
        COMMAND echo "Testing disabled - GTest not found"
        COMMENT "Testing disabled"
    )
    add_custom_target(stress_test
        COMMAND echo "Testing disabled - GTest not found"
        COMMENT "Testing disabled"
    )
    add_custom_target(full_test_suite
        COMMAND echo "Testing disabled - GTest not found"
        COMMENT "Testing disabled"
    )
endif()

# 现代化C++20编译检查
add_custom_target(cpp20_check
    COMMAND ${CMAKE_CXX_COMPILER} --version
    COMMENT "Checking C++20 compiler support"
)

# 代码格式化
add_custom_target(format
    COMMAND find ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/include -name "*.cpp" -o -name "*.hpp" | xargs clang-format -i
    COMMENT "Formatting code with clang-format"
)

# 静态分析
add_custom_target(static_analysis
    COMMAND cppcheck --enable=all --std=c++20 ${CMAKE_SOURCE_DIR}/src/
    COMMENT "Running static analysis with cppcheck"
)