#!/bin/bash

# AI Assistant 增强构建脚本
set -e

# 脚本版本和信息
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="AI Assistant 构建脚本"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✅${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }
log_debug() { [ "$DEBUG" = "true" ] && echo -e "${PURPLE}🐛${NC} $1"; }

# 全局变量
BUILD_TYPE="Release"
JOB_COUNT=$(nproc)
BUILD_DIR="build"
INSTALL_DIR="install"
SKIP_TESTS=false
USE_VENV=false
CLEAN_BUILD=false
DEBUG=false
VERBOSE=false
ENABLE_COVERAGE=false
USE_NINJA=false
ENABLE_SANITIZERS=false

echo -e "${CYAN}🚀 开始构建AI Assistant...${NC}"

# 检查系统依赖
check_system_dependencies() {
    log_info "检查系统依赖..."
    
    local missing_deps=()
    
    # 必需的工具
    local required_tools=("cmake" "python3" "pip3" "make" "g++" "pkg-config")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_deps+=("$tool")
        fi
    done
    
    # 检查可选工具
    if [ "$USE_NINJA" = "true" ]; then
        if ! command -v ninja &> /dev/null; then
            missing_deps+=("ninja")
        fi
    fi
    
    if [ "$ENABLE_COVERAGE" = "true" ]; then
        if ! command -v gcov &> /dev/null; then
            missing_deps+=("gcov")
        fi
    fi
    
    # 报告缺失的依赖
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "以下依赖未安装: ${missing_deps[*]}"
        log_info "Ubuntu/Debian安装命令:"
        echo "  sudo apt-get update"
        echo "  sudo apt-get install -y ${missing_deps[*]}"
        log_info "CentOS/RHEL安装命令:"
        echo "  sudo yum install -y ${missing_deps[*]}"
        exit 1
    fi
    
    # 检查版本要求
    check_version_requirements
    
    log_success "系统依赖检查通过"
}

# 检查版本要求
check_version_requirements() {
    log_debug "检查版本要求..."
    
    # 检查CMake版本
    local cmake_version=$(cmake --version | head -n1 | cut -d' ' -f3)
    local required_cmake="3.20"
    
    if ! version_ge "$cmake_version" "$required_cmake"; then
        log_error "CMake版本过低: $cmake_version (需要 >= $required_cmake)"
        exit 1
    fi
    
    # 检查Python版本
    local python_version=$(python3 --version | cut -d' ' -f2)
    local required_python="3.9"
    
    if ! version_ge "$python_version" "$required_python"; then
        log_error "Python版本过低: $python_version (需要 >= $required_python)"
        exit 1
    fi
    
    log_debug "版本检查通过: CMake $cmake_version, Python $python_version"
}

# 版本比较函数
version_ge() {
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# 设置构建环境
setup_build_environment() {
    log_info "设置构建环境..."
    
    # 清理旧构建文件
    if [ "$CLEAN_BUILD" = "true" ]; then
        log_warning "清理旧构建文件..."
        rm -rf "$BUILD_DIR" "$INSTALL_DIR"
    fi
    
    # 创建构建目录
    mkdir -p "$BUILD_DIR" "$INSTALL_DIR"
    
    # 创建日志目录
    mkdir -p logs
    
    # 设置构建环境变量
    export CC=${CC:-gcc}
    export CXX=${CXX:-g++}
    
    if [ "$ENABLE_SANITIZERS" = "true" ]; then
        export CFLAGS="$CFLAGS -fsanitize=address -fsanitize=undefined"
        export CXXFLAGS="$CXXFLAGS -fsanitize=address -fsanitize=undefined"
        export LDFLAGS="$LDFLAGS -fsanitize=address -fsanitize=undefined"
        log_info "已启用地址和未定义行为检测器"
    fi
    
    cd "$BUILD_DIR"
    log_success "构建环境设置完成"
}

# 构建C++核心模块
build_cpp() {
    log_info "构建C++核心模块..."
    
    local cmake_args=(
        ".."
        "-DCMAKE_BUILD_TYPE=$BUILD_TYPE"
        "-DCMAKE_INSTALL_PREFIX=../$INSTALL_DIR"
        "-DBUILD_TESTS=$([ "$SKIP_TESTS" = "false" ] && echo "ON" || echo "OFF")"
    )
    
    # 添加编译器设置
    cmake_args+=("-DCMAKE_C_COMPILER=$CC")
    cmake_args+=("-DCMAKE_CXX_COMPILER=$CXX")
    
    # 添加覆盖率支持
    if [ "$ENABLE_COVERAGE" = "true" ]; then
        cmake_args+=("-DENABLE_COVERAGE=ON")
    fi
    
    # 选择构建系统
    if [ "$USE_NINJA" = "true" ]; then
        cmake_args+=("-G" "Ninja")
    fi
    
    # 运行CMake配置
    log_debug "CMake配置参数: ${cmake_args[*]}"
    if ! cmake "${cmake_args[@]}"; then
        log_error "CMake配置失败"
        exit 1
    fi
    
    # 编译
    log_info "开始编译 (使用 $JOB_COUNT 个并行任务)..."
    local build_cmd
    if [ "$USE_NINJA" = "true" ]; then
        build_cmd="ninja -j$JOB_COUNT"
    else
        build_cmd="make -j$JOB_COUNT"
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        build_cmd="$build_cmd VERBOSE=1"
    fi
    
    log_debug "编译命令: $build_cmd"
    if ! $build_cmd 2>&1 | tee ../logs/build.log; then
        log_error "编译失败，请查看日志: logs/build.log"
        exit 1
    fi
    
    # 安装
    log_info "安装到目标目录..."
    if [ "$USE_NINJA" = "true" ]; then
        ninja install
    else
        make install
    fi
    
    log_success "C++模块构建完成"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."
    cd ../
    
    # 创建虚拟环境(可选)
    if [ "$USE_VENV" = "true" ]; then
        if [ ! -d "venv" ]; then
            log_info "创建Python虚拟环境..."
            python3 -m venv venv
        fi
        
        log_info "激活虚拟环境..."
        source venv/bin/activate
        
        # 升级pip
        pip install --upgrade pip
        log_success "虚拟环境已创建并激活"
    fi
    
    # 检查requirements.txt
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt文件不存在"
        exit 1
    fi
    
    # 安装依赖
    log_info "安装Python包依赖..."
    local pip_args="install -r requirements.txt"
    
    if [ "$VERBOSE" = "true" ]; then
        pip_args="$pip_args -v"
    fi
    
    if ! pip $pip_args 2>&1 | tee logs/pip_install.log; then
        log_error "Python依赖安装失败，请查看日志: logs/pip_install.log"
        exit 1
    fi
    
    # 验证关键包安装
    verify_python_packages
    
    log_success "Python依赖安装完成"
}

# 验证Python包安装
verify_python_packages() {
    log_debug "验证Python包安装..."
    
    local critical_packages=("fastapi" "uvicorn" "grpcio" "rich" "textual")
    local missing_packages=()
    
    for package in "${critical_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -ne 0 ]; then
        log_error "关键Python包未正确安装: ${missing_packages[*]}"
        exit 1
    fi
    
    log_debug "Python包验证通过"
}

# 运行测试套件
run_tests() {
    log_info "运行测试套件..."
    
    local test_results=()
    local overall_success=true
    
    # C++测试
    if [ -d "$BUILD_DIR" ]; then
        cd "$BUILD_DIR"
        
        if [ -f "ai_assistant_test" ] || [ -f "tests/test_runner" ]; then
            log_info "运行C++单元测试..."
            
            local cpp_test_cmd
            if [ -f "ai_assistant_test" ]; then
                cpp_test_cmd="./ai_assistant_test"
            else
                cpp_test_cmd="./tests/test_runner"
            fi
            
            if $cpp_test_cmd --gtest_output=xml:../logs/cpp_test_results.xml 2>&1 | tee ../logs/cpp_tests.log; then
                test_results+=("C++测试: 通过")
                log_success "C++测试通过"
            else
                test_results+=("C++测试: 失败")
                log_error "C++测试失败"
                overall_success=false
            fi
        else
            log_warning "未找到C++测试可执行文件"
        fi
        
        cd ..
    fi
    
    # Python测试
    if command -v pytest &> /dev/null; then
        log_info "运行Python测试..."
        
        local pytest_args=("tests/" "-v" "--tb=short")
        
        if [ "$ENABLE_COVERAGE" = "true" ]; then
            pytest_args+=("--cov=python" "--cov-report=xml:logs/python_coverage.xml" "--cov-report=html:logs/htmlcov")
        fi
        
        if [ "$VERBOSE" = "true" ]; then
            pytest_args+=("--verbose")
        fi
        
        pytest_args+=("--junitxml=logs/python_test_results.xml")
        
        if python3 -m pytest "${pytest_args[@]}" 2>&1 | tee logs/python_tests.log; then
            test_results+=("Python测试: 通过")
            log_success "Python测试通过"
        else
            test_results+=("Python测试: 失败")
            log_error "Python测试失败"
            overall_success=false
        fi
    else
        log_warning "pytest未安装，跳过Python测试"
    fi
    
    # 显示测试摘要
    display_test_summary "${test_results[@]}"
    
    if [ "$overall_success" = "false" ]; then
        log_error "测试失败，请查看详细日志"
        exit 1
    fi
    
    log_success "所有测试通过"
}

# 显示测试摘要
display_test_summary() {
    echo
    echo -e "${CYAN}📊 测试摘要${NC}"
    echo "=================="
    for result in "$@"; do
        if [[ $result == *"通过"* ]]; then
            echo -e "${GREEN}✅ $result${NC}"
        else
            echo -e "${RED}❌ $result${NC}"
        fi
    done
    echo
}

# 显示帮助信息
show_help() {
    cat << EOF
${SCRIPT_NAME} v${SCRIPT_VERSION}
使用方法: $0 [选项]

构建选项:
  --build-type TYPE     构建类型 (Debug|Release|RelWithDebInfo) [默认: Release]
  --jobs N             并行编译任务数 [默认: $(nproc)]
  --clean              清理旧构建文件
  --ninja              使用Ninja构建系统替代Make
  
Python选项:
  --venv               使用Python虚拟环境
  --skip-python        跳过Python依赖安装
  
测试选项:
  --skip-tests         跳过测试阶段
  --coverage           启用代码覆盖率
  --sanitizers         启用地址和未定义行为检测器
  
调试选项:
  --debug              启用调试输出
  --verbose            详细输出
  --dry-run            仅显示将要执行的命令
  
其他选项:
  --help               显示此帮助信息
  --version            显示版本信息
  
示例:
  $0                          # 标准构建
  $0 --clean --venv           # 清理构建，使用虚拟环境
  $0 --build-type Debug --coverage  # 调试构建，启用覆盖率
  $0 --ninja --jobs 8         # 使用Ninja，8个并行任务
EOF
}

# 显示版本信息
show_version() {
    echo "${SCRIPT_NAME} v${SCRIPT_VERSION}"
    echo "支持的构建系统: Make, Ninja"
    echo "支持的构建类型: Debug, Release, RelWithDebInfo"
}

# 解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-type)
                BUILD_TYPE="$2"
                shift 2
                ;;
            --jobs|-j)
                JOB_COUNT="$2"
                shift 2
                ;;
            --clean)
                CLEAN_BUILD=true
                shift
                ;;
            --ninja)
                USE_NINJA=true
                shift
                ;;
            --venv)
                USE_VENV=true
                shift
                ;;
            --skip-python)
                SKIP_PYTHON=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --coverage)
                ENABLE_COVERAGE=true
                shift
                ;;
            --sanitizers)
                ENABLE_SANITIZERS=true
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            --version)
                show_version
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                echo "使用 --help 查看帮助"
                exit 1
                ;;
        esac
    done
    
    # 验证参数
    case $BUILD_TYPE in
        Debug|Release|RelWithDebInfo)
            ;;
        *)
            log_error "无效的构建类型: $BUILD_TYPE"
            exit 1
            ;;
    esac
    
    if ! [[ "$JOB_COUNT" =~ ^[0-9]+$ ]] || [ "$JOB_COUNT" -le 0 ]; then
        log_error "无效的任务数: $JOB_COUNT"
        exit 1
    fi
}

# 显示构建配置
show_build_config() {
    echo
    echo -e "${CYAN}📋 构建配置${NC}"
    echo "=================="
    echo "构建类型: $BUILD_TYPE"
    echo "并行任务: $JOB_COUNT"
    echo "构建系统: $([ "$USE_NINJA" = "true" ] && echo "Ninja" || echo "Make")"
    echo "虚拟环境: $([ "$USE_VENV" = "true" ] && echo "是" || echo "否")"
    echo "运行测试: $([ "$SKIP_TESTS" = "false" ] && echo "是" || echo "否")"
    echo "代码覆盖率: $([ "$ENABLE_COVERAGE" = "true" ] && echo "是" || echo "否")"
    echo "内存检测器: $([ "$ENABLE_SANITIZERS" = "true" ] && echo "是" || echo "否")"
    echo
}

# 主函数
main() {
    echo -e "${CYAN}${SCRIPT_NAME} v${SCRIPT_VERSION}${NC}"
    echo "==========================================="
    
    # 解析参数
    parse_arguments "$@"
    
    # 显示配置
    show_build_config
    
    # 如果是dry run，仅显示配置
    if [ "$DRY_RUN" = "true" ]; then
        log_info "Dry run模式，不执行实际构建"
        exit 0
    fi
    
    # 记录开始时间
    local start_time=$(date +%s)
    
    # 执行构建步骤
    check_system_dependencies
    setup_build_environment
    build_cpp
    
    if [ "$SKIP_PYTHON" != "true" ]; then
        install_python_deps
    fi
    
    if [ "$SKIP_TESTS" = "false" ]; then
        run_tests
    fi
    
    # 计算构建时间
    local end_time=$(date +%s)
    local build_time=$((end_time - start_time))
    
    # 显示成功信息
    echo
    echo -e "${GREEN}🎉 构建完成！${NC}"
    echo "构建时间: ${build_time}秒"
    echo
    echo -e "${CYAN}📝 下一步:${NC}"
    echo "   1. 运行服务: ./scripts/run_server.sh"
    echo "   2. 启动CLI:  python3 start_cli.py"
    echo "   3. 查看文档: docs/README.md"
    echo "   4. 配置插件: 编辑 src/plugins/"
    
    if [ "$ENABLE_COVERAGE" = "true" ]; then
        echo "   5. 查看覆盖率: open logs/htmlcov/index.html"
    fi
    
    echo
}

# 错误处理函数
handle_error() {
    local exit_code=$?
    local line_number=$1
    
    log_error "构建失败 (退出码: $exit_code, 行号: $line_number)"
    
    # 显示错误上下文
    if [ "$DEBUG" = "true" ]; then
        echo -e "${RED}调试信息:${NC}"
        echo "  - 脚本: $0"
        echo "  - 行号: $line_number"
        echo "  - 退出码: $exit_code"
        echo "  - 当前目录: $(pwd)"
        echo "  - 环境变量: BUILD_TYPE=$BUILD_TYPE, USE_VENV=$USE_VENV"
    fi
    
    log_info "可能的解决方案:"
    echo "  1. 检查依赖是否正确安装"
    echo "  2. 查看详细日志文件: logs/build.log"
    echo "  3. 使用 --debug 参数获取更多信息"
    echo "  4. 清理构建目录后重试: $0 --clean"
    
    exit $exit_code
}

# 设置错误处理
trap 'handle_error $LINENO' ERR

# 设置退出处理
trap 'echo -e "\n${YELLOW}构建过程被中断${NC}"' INT TERM

# 执行主函数
main "$@"