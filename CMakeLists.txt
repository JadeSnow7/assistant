cmake_minimum_required(VERSION 3.20)
project(ai_assistant VERSION 1.0.0 LANGUAGES CXX)

# 设置C++标准
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 编译选项
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -Wall -Wextra")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")

# 查找依赖
find_package(PkgConfig REQUIRED)
find_package(Protobuf REQUIRED)
find_package(gRPC REQUIRED)

# 包含目录
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/cpp/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/cpp/third_party)

# 子项目
add_subdirectory(cpp)

# 安装规则
install(TARGETS ai_assistant_core
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)