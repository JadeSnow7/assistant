cmake_minimum_required(VERSION 3.20)
project(nex_ai_assistant)

# 设置C++标准
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 编译选项
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -mtune=native")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -g -O0 -DDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -DNDEBUG")

# 查找依赖包
find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)
find_package(gRPC REQUIRED)
find_package(Protobuf REQUIRED)
find_package(GTest REQUIRED)

# 查找CUDA（可选）
find_package(CUDA QUIET)
if(CUDA_FOUND)
    enable_language(CUDA)
    add_definitions(-DENABLE_CUDA)
    message(STATUS "CUDA found, enabling GPU acceleration")
else()
    message(STATUS "CUDA not found, GPU acceleration disabled")
endif()

# 包含目录
include_directories(include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# 核心源文件
set(CORE_SOURCES
    src/model_engine.cpp
    src/sys_manager.cpp
    src/plugin_loader.cpp
    src/grpc_server.cpp
    src/common.cpp
)

# 性能优化源文件
set(PERFORMANCE_SOURCES
    src/performance_analyzer.cpp
    src/memory_optimizer.cpp
    src/gpu_engine.cpp
    src/async_scheduler.cpp
    src/model_cache.cpp
    src/benchmark_framework.cpp
    src/optimized_model_engine.cpp
)

# 所有源文件
set(ALL_SOURCES ${CORE_SOURCES} ${PERFORMANCE_SOURCES})

# 核心头文件
set(CORE_HEADERS
    include/model_engine.hpp
    include/sys_manager.hpp
    include/plugin_loader.hpp
    include/grpc_server.hpp
    include/common.hpp
)

# 性能优化头文件
set(PERFORMANCE_HEADERS
    include/performance_analyzer.hpp
    include/memory_optimizer.hpp
    include/gpu_engine.hpp
    include/async_scheduler.hpp
    include/model_cache.hpp
    include/benchmark_framework.hpp
    include/optimized_model_engine.hpp
)

# 所有头文件
set(ALL_HEADERS ${CORE_HEADERS} ${PERFORMANCE_HEADERS})

# 创建核心库
add_library(ai_assistant_core SHARED ${ALL_SOURCES} ${ALL_HEADERS})

# 设置库属性
set_target_properties(ai_assistant_core PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    PUBLIC_HEADER "${ALL_HEADERS}"
)

# 链接库
target_link_libraries(ai_assistant_core
    PUBLIC
    gRPC::grpc++
    protobuf::libprotobuf
    Threads::Threads
    ${CMAKE_DL_LIBS}
)

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
target_link_libraries(ai_assistant_server ai_assistant_core)

# 性能测试可执行文件
add_executable(performance_tests
    tests/performance_integration_tests.cpp
)
target_link_libraries(performance_tests
    ai_assistant_core
    GTest::gtest
    GTest::gtest_main
)

# 安装配置
install(TARGETS ai_assistant_core ai_assistant_server
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
    PUBLIC_HEADER DESTINATION include/ai_assistant
)

# 测试
enable_testing()
add_test(NAME PerformanceIntegrationTests COMMAND performance_tests)

# 性能基准测试目标
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