cmake_minimum_required(VERSION 3.20)

# 源文件
set(SOURCES
    src/model_engine.cpp
    src/sys_manager.cpp
    src/plugin_loader.cpp
    src/grpc_server.cpp
    src/main.cpp
)

# 头文件
set(HEADERS
    include/model_engine.hpp
    include/sys_manager.hpp
    include/plugin_loader.hpp
    include/grpc_server.hpp
    include/common.hpp
)

# 创建库
add_library(ai_assistant_core SHARED ${SOURCES} ${HEADERS})

# 链接库
target_link_libraries(ai_assistant_core
    gRPC::grpc++
    protobuf::libprotobuf
    ${CMAKE_DL_LIBS}
)

# 可执行文件
add_executable(ai_assistant_server src/main.cpp)
target_link_libraries(ai_assistant_server ai_assistant_core)

# 测试
enable_testing()
add_subdirectory(tests)