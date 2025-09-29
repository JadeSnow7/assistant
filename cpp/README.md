# C++重构项目README

本文档描述了基于设计文档实现的hushell AI助手系统C++重构项目的构建、测试和部署指南。

## 📋 项目概述

hushell C++重构项目实现了以下关键特性：

### 🏗️ 架构特性
- **现代C++20**: 使用协程、概念约束、模块系统等现代特性
- **跨平台支持**: Linux、Windows、macOS专门优化
- **模块化设计**: 清晰的组件边界和接口定义
- **异步编程**: 基于协程的高性能异步系统
- **内存管理**: 智能对象池和高性能分配器

### 🚀 核心组件
- **异步类型系统** (`core/async_types.hpp`): Task和Result类型
- **内存管理器** (`core/memory_manager.hpp`): 对象池和GPU内存管理
- **任务调度器** (`core/scheduler.hpp`): 工作窃取线程池
- **平台适配器** (`platform/`): 跨平台系统操作抽象
- **插件系统** (`plugin/`): C++和Python插件支持
- **gRPC服务** (`core/grpc_service.hpp`): 高性能通信接口
- **测试框架** (`testing/`): 完整的单元和性能测试

## 🛠️ 构建要求

### 系统要求
- **操作系统**: Linux (Ubuntu 20.04+), Windows 10+, macOS 11+
- **编译器**: 
  - GCC 10.0+ (Linux)
  - Clang 12.0+ (macOS/Linux)
  - MSVC 19.29+ (Windows)
- **CMake**: 3.20+

### 依赖库
```bash
# Ubuntu/Debian
sudo apt-get install cmake build-essential pkg-config libgtest-dev

# CentOS/RHEL
sudo yum install cmake gcc-c++ pkg-config gtest-devel

# macOS
brew install cmake pkg-config googletest

# Windows (vcpkg)
vcpkg install gtest grpc protobuf
```

### 可选依赖
- **gRPC + Protobuf**: 启用RPC通信功能
- **CUDA Toolkit**: 启用GPU加速
- **Google Benchmark**: 性能基准测试
- **nlohmann/json**: JSON配置支持

## 🔧 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd nex/cpp
```

### 2. 基础构建
```bash
# 使用构建脚本（推荐）
./build_and_test.sh

# 或手动构建
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

### 3. 运行测试
```bash
# 运行所有测试
./build_and_test.sh --integration

# 仅单元测试
./build/performance_tests

# 性能基准测试
./build_and_test.sh --benchmark
```

## 📊 构建选项

### 构建脚本选项
```bash
./build_and_test.sh [选项]

选项:
  -h, --help              显示帮助信息
  -c, --clean             清理构建目录
  -d, --debug             Debug构建
  -r, --release           Release构建
  -j, --jobs N            并行任务数
  --coverage              启用代码覆盖率
  --sanitizers            启用内存检测器
  --benchmark             运行基准测试
  --integration           运行集成测试
```

### CMake选项
```bash
# 基础选项
-DCMAKE_BUILD_TYPE=Release|Debug|RelWithDebInfo
-DBUILD_TESTING=ON|OFF
-DENABLE_GRPC_FEATURES=ON|OFF

# 高级选项
-DENABLE_COVERAGE=ON         # 代码覆盖率
-DENABLE_SANITIZERS=ON       # 内存检测器
-DCMAKE_CUDA_ARCHITECTURES="70;75;80;86"  # CUDA架构
```

## 🧪 测试套件

### 测试类型
1. **单元测试**: 核心组件功能测试
2. **集成测试**: 组件间交互测试
3. **性能测试**: 基准测试和压力测试
4. **平台测试**: 跨平台兼容性测试

### 测试运行
```bash
# 完整测试套件
./build_and_test.sh --integration --benchmark --coverage

# 特定测试
./build/performance_tests --gtest_filter="*Async*"
./build/integration_test
```

### 测试报告
测试结果保存在 `build/test_results/`:
- `unit_tests.xml`: 单元测试结果
- `benchmark_tests.xml`: 基准测试结果
- `integration_tests.xml`: 集成测试结果
- `build_report.txt`: 构建摘要报告

## 📈 性能基准

### 关键指标
- **Task创建**: < 100微秒/任务
- **Result链式操作**: < 1微秒/操作
- **内存分配**: < 10微秒/分配
- **并发调度**: 支持10,000+并发任务

### 基准测试
```bash
# 运行所有基准测试
./build_and_test.sh --benchmark

# 查看基准结果
cat build/test_results/benchmark_tests.xml
```

## 🔧 开发指南

### 代码结构
```
cpp/
├── include/nex/           # 头文件
│   ├── core/             # 核心组件
│   ├── platform/         # 平台适配
│   ├── plugin/           # 插件系统
│   └── testing/          # 测试框架
├── src/                  # 实现文件
├── tests/                # 测试代码
├── cmake/                # CMake模块
└── build_and_test.sh     # 构建脚本
```

### 编码规范
- **C++20标准**: 使用现代C++特性
- **命名约定**: snake_case for variables, PascalCase for classes
- **内存管理**: 优先使用智能指针和RAII
- **异常安全**: 使用Result<T>类型代替异常
- **文档**: 所有公共API必须有文档注释

### 添加新组件
1. 在 `include/nex/` 下创建头文件
2. 在 `src/` 下实现功能
3. 在 `tests/` 下添加测试
4. 更新CMakeLists.txt
5. 运行完整测试套件

## 🚀 部署

### 构建产物
- `ai_assistant_server`: 主服务器可执行文件
- `libnex_*.so`: 模块化库文件
- `ai_assistant_core.so`: 核心库

### 安装
```bash
# 安装到系统
cd build
sudo make install

# 或创建安装包
cpack
```

### 配置
主要配置文件:
- 系统配置: `/etc/hushell/`
- 用户配置: `~/.config/hushell/`
- 临时文件: `/tmp/hushell/`

## 🐛 故障排除

### 常见问题

**1. 编译错误: "C++20 features not supported"**
```bash
# 检查编译器版本
g++ --version   # 需要 >= 10.0
clang++ --version  # 需要 >= 12.0

# 更新编译器
sudo apt-get install gcc-10 g++-10  # Ubuntu
```

**2. CMake配置失败**
```bash
# 清理CMake缓存
rm -rf build/CMakeCache.txt build/CMakeFiles/
./build_and_test.sh --clean
```

**3. 链接错误: 找不到库**
```bash
# 检查依赖
ldd build/ai_assistant_server
# 安装缺失的库
sudo apt-get install libgtest-dev libgrpc++-dev
```

**4. 测试失败**
```bash
# 运行详细测试
./build/performance_tests --gtest_output=xml --gtest_verbose
# 检查测试日志
cat build/test_results/*.xml
```

### 性能调优

**1. 内存使用优化**
```bash
# 启用内存检测
./build_and_test.sh --sanitizers
# 监控内存使用
valgrind --tool=memcheck ./build/ai_assistant_server
```

**2. CPU使用优化**
```bash
# 性能分析
perf record ./build/performance_tests
perf report
```

**3. GPU加速**
```bash
# 检查CUDA支持
nvidia-smi
# 启用GPU
cmake -DENABLE_CUDA=ON ..
```

## 📞 支持

### 文档
- [设计文档](../docs/cpp_refactor_design.md)
- [API参考](build/docs/html/index.html)
- [架构说明](../docs/architecture.md)

### 社区
- GitHub Issues: 报告bug和功能请求
- Discussions: 技术讨论和问答
- Wiki: 详细的开发文档

### 贡献
1. Fork项目
2. 创建功能分支
3. 提交代码和测试
4. 创建Pull Request

---

## 📄 许可证

本项目基于MIT许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。