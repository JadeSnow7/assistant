#!/bin/bash

# nex项目性能优化实施脚本
# 此脚本用于部署和验证所有性能优化组件

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查系统依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查CMake版本
    if ! command -v cmake &> /dev/null; then
        log_error "CMake未安装"
        exit 1
    fi
    
    CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
    log_info "CMake版本: $CMAKE_VERSION"
    
    # 检查C++编译器
    if ! command -v g++ &> /dev/null; then
        log_error "g++编译器未安装"
        exit 1
    fi
    
    GCC_VERSION=$(g++ --version | head -n1)
    log_info "编译器: $GCC_VERSION"
    
    # 检查CUDA（可选）
    if command -v nvcc &> /dev/null; then
        CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $6}' | cut -c2-)
        log_success "检测到CUDA版本: $CUDA_VERSION"
    else
        log_warning "未检测到CUDA，将禁用GPU加速功能"
    fi
    
    # 检查内存
    TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    log_info "系统内存: ${TOTAL_MEM}GB"
    
    if [ "$TOTAL_MEM" -lt 8 ]; then
        log_warning "系统内存不足8GB，性能可能受限"
    fi
    
    log_success "依赖检查完成"
}

# 创建构建目录
setup_build_directory() {
    log_info "创建构建目录..."
    
    BUILD_DIR="build_performance"
    
    if [ -d "$BUILD_DIR" ]; then
        log_warning "构建目录已存在，正在清理..."
        rm -rf "$BUILD_DIR"
    fi
    
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    
    log_success "构建目录创建完成: $PWD"
}

# 配置CMake
configure_cmake() {
    log_info "配置CMake构建..."
    
    CMAKE_OPTIONS=""
    
    # 检查是否支持CUDA
    if command -v nvcc &> /dev/null; then
        CMAKE_OPTIONS="$CMAKE_OPTIONS -DENABLE_CUDA=ON"
        log_info "启用CUDA支持"
    fi
    
    # 设置优化级别
    CMAKE_OPTIONS="$CMAKE_OPTIONS -DCMAKE_BUILD_TYPE=Release"
    CMAKE_OPTIONS="$CMAKE_OPTIONS -DCMAKE_CXX_FLAGS_RELEASE=-O3 -march=native -mtune=native"
    
    log_info "CMake配置选项: $CMAKE_OPTIONS"
    
    cmake .. $CMAKE_OPTIONS
    
    if [ $? -eq 0 ]; then
        log_success "CMake配置成功"
    else
        log_error "CMake配置失败"
        exit 1
    fi
}

# 编译项目
build_project() {
    log_info "编译项目..."
    
    # 获取CPU核心数用于并行编译
    CORES=$(nproc)
    log_info "使用 $CORES 个核心进行并行编译"
    
    make -j$CORES
    
    if [ $? -eq 0 ]; then
        log_success "项目编译成功"
    else
        log_error "项目编译失败"
        exit 1
    fi
}

# 运行基础性能测试
run_basic_tests() {
    log_info "运行基础性能测试..."
    
    if [ -f "./performance_tests" ]; then
        ./performance_tests --gtest_filter="*BasicPerformance*"
        
        if [ $? -eq 0 ]; then
            log_success "基础性能测试通过"
        else
            log_error "基础性能测试失败"
            return 1
        fi
    else
        log_error "性能测试可执行文件不存在"
        return 1
    fi
}

# 运行GPU加速测试
run_gpu_tests() {
    if command -v nvidia-smi &> /dev/null; then
        log_info "运行GPU加速测试..."
        
        ./performance_tests --gtest_filter="*GPU*"
        
        if [ $? -eq 0 ]; then
            log_success "GPU加速测试通过"
        else
            log_warning "GPU加速测试失败，但继续执行"
        fi
    else
        log_info "跳过GPU测试（未检测到NVIDIA GPU）"
    fi
}

# 运行内存优化测试
run_memory_tests() {
    log_info "运行内存优化测试..."
    
    ./performance_tests --gtest_filter="*Memory*"
    
    if [ $? -eq 0 ]; then
        log_success "内存优化测试通过"
    else
        log_error "内存优化测试失败"
        return 1
    fi
}

# 运行异步处理测试
run_async_tests() {
    log_info "运行异步处理测试..."
    
    ./performance_tests --gtest_filter="*Async*"
    
    if [ $? -eq 0 ]; then
        log_success "异步处理测试通过"
    else
        log_error "异步处理测试失败"
        return 1
    fi
}

# 运行压力测试
run_stress_tests() {
    log_info "运行压力测试..."
    
    ./performance_tests --gtest_filter="*Stress*"
    
    if [ $? -eq 0 ]; then
        log_success "压力测试通过"
    else
        log_warning "压力测试失败，但继续执行"
    fi
}

# 运行完整基准测试
run_benchmark_tests() {
    log_info "运行完整基准测试..."
    
    ./performance_tests --gtest_filter="*Benchmark*"
    
    if [ $? -eq 0 ]; then
        log_success "基准测试完成"
    else
        log_warning "基准测试部分失败"
    fi
}

# 生成性能报告
generate_performance_report() {
    log_info "生成性能报告..."
    
    REPORT_DIR="../performance_reports"
    mkdir -p "$REPORT_DIR"
    
    # 运行完整测试套件并保存结果
    ./performance_tests > "$REPORT_DIR/performance_test_results.txt" 2>&1
    
    # 获取系统信息
    {
        echo "=== 系统信息 ==="
        echo "操作系统: $(uname -a)"
        echo "CPU信息: $(lscpu | grep 'Model name' | cut -d':' -f2- | xargs)"
        echo "CPU核心数: $(nproc)"
        echo "内存信息: $(free -h | grep '^Mem:')"
        echo "磁盘信息: $(df -h / | tail -1)"
        
        if command -v nvidia-smi &> /dev/null; then
            echo "GPU信息:"
            nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
        fi
        
        echo ""
        echo "=== 编译信息 ==="
        echo "编译器版本: $(g++ --version | head -1)"
        echo "CMake版本: $(cmake --version | head -1)"
        echo "构建类型: Release"
        echo "优化选项: -O3 -march=native -mtune=native"
        
    } > "$REPORT_DIR/system_info.txt"
    
    log_success "性能报告已生成: $REPORT_DIR/"
}

# 部署验证
validate_deployment() {
    log_info "验证部署..."
    
    # 检查可执行文件
    if [ -f "./ai_assistant_server" ]; then
        log_success "主服务器可执行文件已生成"
    else
        log_error "主服务器可执行文件缺失"
        return 1
    fi
    
    # 检查库文件
    if [ -f "./libai_assistant_core.so" ]; then
        log_success "核心库文件已生成"
    else
        log_error "核心库文件缺失"
        return 1
    fi
    
    # 检查测试文件
    if [ -f "./performance_tests" ]; then
        log_success "性能测试文件已生成"
    else
        log_error "性能测试文件缺失"
        return 1
    fi
    
    log_success "部署验证完成"
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    cd ..
    # 可以选择保留构建目录用于后续分析
    # rm -rf "$BUILD_DIR"
    log_success "清理完成"
}

# 主函数
main() {
    echo "=========================================="
    echo "    nex项目性能优化实施脚本"
    echo "=========================================="
    echo ""
    
    # 记录开始时间
    START_TIME=$(date +%s)
    
    # 执行步骤
    check_dependencies
    setup_build_directory
    configure_cmake
    build_project
    validate_deployment
    
    echo ""
    log_info "开始运行性能测试套件..."
    echo "=========================================="
    
    run_basic_tests
    run_gpu_tests
    run_memory_tests
    run_async_tests
    run_stress_tests
    run_benchmark_tests
    
    generate_performance_report
    
    # 计算总耗时
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo "=========================================="
    log_success "性能优化实施完成!"
    log_info "总耗时: ${DURATION}秒"
    log_info "构建目录: $(pwd)"
    log_info "性能报告目录: ../performance_reports/"
    echo "=========================================="
    
    # 显示下一步建议
    echo ""
    log_info "下一步建议:"
    echo "1. 查看性能报告: cat ../performance_reports/performance_test_results.txt"
    echo "2. 运行服务器: ./ai_assistant_server"
    echo "3. 运行特定测试: ./performance_tests --gtest_filter='*TestName*'"
    echo "4. 运行基准测试: make benchmark"
    echo "5. 运行压力测试: make stress_test"
}

# 捕获信号以便清理
trap cleanup EXIT

# 运行主函数
main "$@"