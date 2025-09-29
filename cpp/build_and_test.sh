#!/bin/bash

# C++重构构建和测试脚本
# 基于设计文档的完整构建流程

set -e  # 出错时退出

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/build"
TEST_OUTPUT_DIR="$BUILD_DIR/test_results"

# 颜色输出
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

# 显示帮助信息
show_help() {
    cat << EOF
hushell C++重构构建和测试脚本

用法: $0 [选项]

选项:
    -h, --help              显示此帮助信息
    -c, --clean             清理构建目录
    -d, --debug             使用Debug构建类型
    -r, --release           使用Release构建类型
    -t, --test-only         仅运行测试，不重新构建
    -b, --build-only        仅构建，不运行测试
    -j, --jobs N            并行构建任务数（默认：CPU核心数）
    -v, --verbose           详细输出
    --coverage              启用代码覆盖率
    --sanitizers            启用检测器
    --benchmark             运行性能基准测试
    --integration           运行集成测试

示例:
    $0                      # 默认构建和测试
    $0 -r --benchmark       # Release构建并运行基准测试
    $0 -c -d --coverage     # 清理后Debug构建并启用覆盖率
    $0 --integration        # 运行集成测试

EOF
}

# 默认配置
BUILD_TYPE="RelWithDebInfo"
CLEAN_BUILD=false
TEST_ONLY=false
BUILD_ONLY=false
JOBS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
VERBOSE=false
ENABLE_COVERAGE=false
ENABLE_SANITIZERS=false
RUN_BENCHMARKS=false
RUN_INTEGRATION=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -d|--debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        -r|--release)
            BUILD_TYPE="Release"
            shift
            ;;
        -t|--test-only)
            TEST_ONLY=true
            shift
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -j|--jobs)
            JOBS="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --coverage)
            ENABLE_COVERAGE=true
            BUILD_TYPE="Debug"  # 覆盖率需要Debug符号
            shift
            ;;
        --sanitizers)
            ENABLE_SANITIZERS=true
            BUILD_TYPE="Debug"  # 检测器需要Debug符号
            shift
            ;;
        --benchmark)
            RUN_BENCHMARKS=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查依赖
check_dependencies() {
    log_info "检查构建依赖..."
    
    local missing_deps=()
    
    # 检查必要工具
    command -v cmake >/dev/null 2>&1 || missing_deps+=("cmake")
    command -v make >/dev/null 2>&1 || command -v ninja >/dev/null 2>&1 || missing_deps+=("make or ninja")
    
    # 检查编译器
    if command -v g++ >/dev/null 2>&1; then
        GCC_VERSION=$(g++ --version | head -n1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        if [[ $(echo "$GCC_VERSION >= 10.0" | bc -l 2>/dev/null || echo 0) -eq 0 ]]; then
            log_warning "GCC版本 $GCC_VERSION 可能不支持C++20，建议使用GCC 10.0+"
        fi
    elif command -v clang++ >/dev/null 2>&1; then
        CLANG_VERSION=$(clang++ --version | head -n1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        if [[ $(echo "$CLANG_VERSION >= 12.0" | bc -l 2>/dev/null || echo 0) -eq 0 ]]; then
            log_warning "Clang版本 $CLANG_VERSION 可能不支持C++20，建议使用Clang 12.0+"
        fi
    else
        missing_deps+=("g++ or clang++")
    fi
    
    # 检查pkg-config
    command -v pkg-config >/dev/null 2>&1 || missing_deps+=("pkg-config")
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "缺少以下依赖: ${missing_deps[*]}"
        log_info "Ubuntu/Debian: sudo apt-get install cmake build-essential pkg-config"
        log_info "CentOS/RHEL: sudo yum install cmake gcc-c++ pkg-config"
        log_info "macOS: brew install cmake pkg-config"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 检测构建系统
detect_build_system() {
    if command -v ninja >/dev/null 2>&1; then
        BUILD_SYSTEM="Ninja"
        GENERATOR="Ninja"
        BUILD_COMMAND="ninja"
    else
        BUILD_SYSTEM="Make"
        GENERATOR="Unix Makefiles"
        BUILD_COMMAND="make"
    fi
    
    log_info "使用构建系统: $BUILD_SYSTEM"
}

# 清理构建目录
clean_build() {
    if [[ "$CLEAN_BUILD" == true ]]; then
        log_info "清理构建目录..."
        rm -rf "$BUILD_DIR"
        log_success "构建目录已清理"
    fi
}

# 创建构建目录
create_build_dir() {
    log_info "创建构建目录..."
    mkdir -p "$BUILD_DIR"
    mkdir -p "$TEST_OUTPUT_DIR"
}

# 配置CMake
configure_cmake() {
    log_info "配置CMake (构建类型: $BUILD_TYPE)..."
    
    cd "$BUILD_DIR"
    
    local cmake_args=(
        "-DCMAKE_BUILD_TYPE=$BUILD_TYPE"
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
        "-G$GENERATOR"
    )
    
    # 启用测试
    cmake_args+=("-DBUILD_TESTING=ON")
    
    # 代码覆盖率
    if [[ "$ENABLE_COVERAGE" == true ]]; then
        cmake_args+=("-DENABLE_COVERAGE=ON")
        log_info "启用代码覆盖率"
    fi
    
    # 检测器
    if [[ "$ENABLE_SANITIZERS" == true ]]; then
        cmake_args+=("-DENABLE_SANITIZERS=ON")
        log_info "启用检测器"
    fi
    
    # 详细输出
    if [[ "$VERBOSE" == true ]]; then
        cmake_args+=("-DCMAKE_VERBOSE_MAKEFILE=ON")
    fi
    
    # 运行CMake配置
    if [[ "$VERBOSE" == true ]]; then
        cmake "${cmake_args[@]}" "$SCRIPT_DIR"
    else
        cmake "${cmake_args[@]}" "$SCRIPT_DIR" > cmake_config.log 2>&1
    fi
    
    if [[ $? -eq 0 ]]; then
        log_success "CMake配置完成"
    else
        log_error "CMake配置失败"
        if [[ "$VERBOSE" == false ]]; then
            log_info "查看详细错误: cat $BUILD_DIR/cmake_config.log"
        fi
        exit 1
    fi
}

# 构建项目
build_project() {
    if [[ "$TEST_ONLY" == true ]]; then
        log_info "跳过构建，仅运行测试"
        return 0
    fi
    
    log_info "构建项目 (使用 $JOBS 个并行任务)..."
    
    cd "$BUILD_DIR"
    
    local build_args=()
    
    if [[ "$BUILD_SYSTEM" == "Ninja" ]]; then
        build_args+=("-j$JOBS")
    else
        build_args+=("-j$JOBS")
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        build_args+=("-v")
    fi
    
    # 构建
    local start_time=$(date +%s)
    
    if [[ "$VERBOSE" == true ]]; then
        $BUILD_COMMAND "${build_args[@]}"
    else
        $BUILD_COMMAND "${build_args[@]}" > build.log 2>&1
    fi
    
    local build_result=$?
    local end_time=$(date +%s)
    local build_duration=$((end_time - start_time))
    
    if [[ $build_result -eq 0 ]]; then
        log_success "构建完成 (耗时: ${build_duration}秒)"
    else
        log_error "构建失败"
        if [[ "$VERBOSE" == false ]]; then
            log_info "查看详细错误: cat $BUILD_DIR/build.log"
        fi
        exit 1
    fi
}

# 运行单元测试
run_unit_tests() {
    if [[ "$BUILD_ONLY" == true ]]; then
        log_info "跳过测试，仅构建"
        return 0
    fi
    
    log_info "运行单元测试..."
    
    cd "$BUILD_DIR"
    
    # 检查是否有测试可执行文件
    if [[ ! -f "performance_tests" ]]; then
        log_warning "未找到测试可执行文件，跳过单元测试"
        return 0
    fi
    
    # 运行测试
    local test_start_time=$(date +%s)
    
    # 设置测试环境变量
    export GTEST_OUTPUT="xml:$TEST_OUTPUT_DIR/unit_tests.xml"
    export GTEST_COLOR=yes
    
    if ./performance_tests --gtest_filter="-*Benchmark*" ; then
        local test_end_time=$(date +%s)
        local test_duration=$((test_end_time - test_start_time))
        log_success "单元测试通过 (耗时: ${test_duration}秒)"
    else
        log_error "单元测试失败"
        exit 1
    fi
}

# 运行基准测试
run_benchmarks() {
    if [[ "$RUN_BENCHMARKS" != true ]]; then
        return 0
    fi
    
    log_info "运行性能基准测试..."
    
    cd "$BUILD_DIR"
    
    if [[ ! -f "performance_tests" ]]; then
        log_warning "未找到性能测试可执行文件"
        return 0
    fi
    
    export GTEST_OUTPUT="xml:$TEST_OUTPUT_DIR/benchmark_tests.xml"
    
    if ./performance_tests --gtest_filter="*Benchmark*" ; then
        log_success "基准测试完成"
    else
        log_error "基准测试失败"
        exit 1
    fi
}

# 运行集成测试
run_integration_tests() {
    if [[ "$RUN_INTEGRATION" != true ]]; then
        return 0
    fi
    
    log_info "运行集成测试..."
    
    cd "$BUILD_DIR"
    
    if [[ ! -f "integration_test" ]]; then
        log_warning "未找到集成测试可执行文件"
        return 0
    fi
    
    export GTEST_OUTPUT="xml:$TEST_OUTPUT_DIR/integration_tests.xml"
    
    if ./integration_test ; then
        log_success "集成测试通过"
    else
        log_error "集成测试失败"
        exit 1
    fi
}

# 生成代码覆盖率报告
generate_coverage_report() {
    if [[ "$ENABLE_COVERAGE" != true ]]; then
        return 0
    fi
    
    log_info "生成代码覆盖率报告..."
    
    cd "$BUILD_DIR"
    
    # 检查gcov工具
    if ! command -v gcov >/dev/null 2>&1; then
        log_warning "未找到gcov，跳过覆盖率报告"
        return 0
    fi
    
    # 生成覆盖率数据
    if command -v lcov >/dev/null 2>&1; then
        lcov --capture --directory . --output-file coverage.info
        lcov --remove coverage.info '/usr/*' '*/tests/*' '*/third_party/*' --output-file coverage_filtered.info
        
        if command -v genhtml >/dev/null 2>&1; then
            genhtml coverage_filtered.info --output-directory coverage_html
            log_success "覆盖率报告生成: $BUILD_DIR/coverage_html/index.html"
        fi
    else
        log_warning "未安装lcov，使用基本gcov"
        find . -name "*.gcda" -exec gcov {} \;
    fi
}

# 检查内存泄漏
check_memory_leaks() {
    if [[ "$ENABLE_SANITIZERS" != true ]]; then
        return 0
    fi
    
    log_info "检查内存泄漏..."
    
    # AddressSanitizer和其他检测器会在运行时报告问题
    # 这里主要是确认检测器正常工作
    
    cd "$BUILD_DIR"
    
    if [[ -f "performance_tests" ]]; then
        log_info "运行带检测器的测试..."
        # 设置ASAN选项
        export ASAN_OPTIONS="detect_leaks=1:abort_on_error=1"
        export UBSAN_OPTIONS="abort_on_error=1"
        
        # 运行一个简单的测试
        if ./performance_tests --gtest_filter="*Basic*" > sanitizer.log 2>&1; then
            log_success "内存检查通过"
        else
            log_error "检测到内存问题"
            cat sanitizer.log
            exit 1
        fi
    fi
}

# 生成构建报告
generate_build_report() {
    log_info "生成构建报告..."
    
    local report_file="$TEST_OUTPUT_DIR/build_report.txt"
    
    cat > "$report_file" << EOF
=== hushell C++重构构建报告 ===

构建时间: $(date)
构建类型: $BUILD_TYPE
构建系统: $BUILD_SYSTEM
并行任务: $JOBS

平台信息:
- 操作系统: $(uname -s)
- 架构: $(uname -m)
- 内核版本: $(uname -r)

编译器信息:
EOF

    if command -v g++ >/dev/null 2>&1; then
        echo "- GCC: $(g++ --version | head -n1)" >> "$report_file"
    fi
    
    if command -v clang++ >/dev/null 2>&1; then
        echo "- Clang: $(clang++ --version | head -n1)" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

CMake版本: $(cmake --version | head -n1)

构建选项:
- 代码覆盖率: $ENABLE_COVERAGE
- 检测器: $ENABLE_SANITIZERS
- 基准测试: $RUN_BENCHMARKS
- 集成测试: $RUN_INTEGRATION

构建产物:
EOF
    
    cd "$BUILD_DIR"
    find . -name "*.so" -o -name "*.a" -o -name "ai_assistant_*" | sort >> "$report_file"
    
    echo "" >> "$report_file"
    echo "测试结果:" >> "$report_file"
    
    if [[ -f "$TEST_OUTPUT_DIR/unit_tests.xml" ]]; then
        echo "- 单元测试: 完成" >> "$report_file"
    fi
    
    if [[ -f "$TEST_OUTPUT_DIR/benchmark_tests.xml" ]]; then
        echo "- 基准测试: 完成" >> "$report_file"
    fi
    
    if [[ -f "$TEST_OUTPUT_DIR/integration_tests.xml" ]]; then
        echo "- 集成测试: 完成" >> "$report_file"
    fi
    
    log_success "构建报告生成: $report_file"
}

# 显示总结信息
show_summary() {
    echo ""
    echo "==============================================="
    log_success "hushell C++重构构建完成！"
    echo "==============================================="
    echo ""
    
    log_info "构建类型: $BUILD_TYPE"
    log_info "构建目录: $BUILD_DIR"
    log_info "测试结果: $TEST_OUTPUT_DIR"
    
    if [[ -d "$BUILD_DIR/coverage_html" ]]; then
        log_info "覆盖率报告: $BUILD_DIR/coverage_html/index.html"
    fi
    
    echo ""
    log_info "主要可执行文件:"
    cd "$BUILD_DIR"
    if [[ -f "ai_assistant_server" ]]; then
        echo "  - ai_assistant_server (主服务器)"
    fi
    if [[ -f "performance_tests" ]]; then
        echo "  - performance_tests (性能测试)"
    fi
    if [[ -f "integration_test" ]]; then
        echo "  - integration_test (集成测试)"
    fi
    
    echo ""
    log_info "库文件:"
    find . -name "lib*.so" -o -name "lib*.a" | sort | sed 's/^/  - /'
    
    echo ""
    echo "==============================================="
}

# 主执行流程
main() {
    log_info "开始hushell C++重构构建和测试..."
    
    # 检查和准备
    check_dependencies
    detect_build_system
    clean_build
    create_build_dir
    
    # 配置和构建
    configure_cmake
    build_project
    
    # 测试
    run_unit_tests
    run_benchmarks
    run_integration_tests
    
    # 分析
    generate_coverage_report
    check_memory_leaks
    
    # 报告
    generate_build_report
    show_summary
    
    log_success "所有任务完成！"
}

# 异常处理
trap 'log_error "构建过程中断"; exit 1' INT TERM

# 执行主流程
main "$@"