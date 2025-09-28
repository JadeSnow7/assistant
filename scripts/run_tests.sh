#!/bin/bash

# 整体测试脚本
# 执行完整的测试套件，包括单元测试、集成测试、CLI测试等

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"
COVERAGE_DIR="$PROJECT_ROOT/coverage"
REPORT_FILE="$TEST_RESULTS_DIR/test-report.json"

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

# 检查前置条件
check_prerequisites() {
    log_info "检查测试前置条件..."
    
    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    # 检查必要的包
    local required_packages=("pytest" "pytest-cov" "pytest-asyncio" "pytest-xdist")
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            log_warning "$package 未安装，正在安装..."
            pip install "$package"
        fi
    done
    
    # 检查项目结构
    if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
        log_warning "requirements.txt 不存在"
    fi
    
    if [ ! -d "$PROJECT_ROOT/python" ]; then
        log_error "Python源码目录不存在"
        exit 1
    fi
    
    log_success "前置条件检查完成"
}

# 准备测试环境
setup_test_environment() {
    log_info "准备测试环境..."
    
    # 创建测试结果目录
    mkdir -p "$TEST_RESULTS_DIR" "$COVERAGE_DIR"
    
    # 设置Python路径
    export PYTHONPATH="$PROJECT_ROOT/python:$PYTHONPATH"
    
    # 创建测试数据库目录
    mkdir -p "$PROJECT_ROOT/test-data"
    
    # 复制测试配置文件
    if [ -f "$PROJECT_ROOT/.env.test" ]; then
        cp "$PROJECT_ROOT/.env.test" "$PROJECT_ROOT/.env"
    fi
    
    log_success "测试环境准备完成"
}

# 运行单元测试
run_unit_tests() {
    log_info "运行单元测试..."
    
    cd "$PROJECT_ROOT"
    
    # 运行Python单元测试
    if [ -d "tests/unit" ]; then
        python3 -m pytest tests/unit/ \
            --cov=python \
            --cov-report=html:$COVERAGE_DIR/unit \
            --cov-report=xml:$COVERAGE_DIR/unit-coverage.xml \
            --junit-xml=$TEST_RESULTS_DIR/unit-results.xml \
            --tb=short \
            -v \
            || {
                log_error "单元测试失败"
                return 1
            }
        
        log_success "单元测试通过"
    else
        log_warning "未找到单元测试目录"
    fi
}

# 运行集成测试
run_integration_tests() {
    log_info "运行集成测试..."
    
    cd "$PROJECT_ROOT"
    
    # 启动测试服务
    log_info "启动测试服务..."
    python3 python/main.py &
    local server_pid=$!
    
    # 等待服务启动
    local timeout=30
    local count=0
    while ! curl -f -s http://localhost:8000/health >/dev/null 2>&1; do
        if [ $count -ge $timeout ]; then
            log_error "测试服务启动超时"
            kill $server_pid 2>/dev/null || true
            return 1
        fi
        sleep 1
        ((count++))
    done
    
    log_success "测试服务已启动"
    
    # 运行集成测试
    if [ -d "tests/integration" ]; then
        python3 -m pytest tests/integration/ \
            --junit-xml=$TEST_RESULTS_DIR/integration-results.xml \
            --tb=short \
            -v \
            || {
                log_error "集成测试失败"
                kill $server_pid 2>/dev/null || true
                return 1
            }
        
        log_success "集成测试通过"
    else
        log_warning "未找到集成测试目录"
    fi
    
    # 停止测试服务
    kill $server_pid 2>/dev/null || true
    wait $server_pid 2>/dev/null || true
    log_info "测试服务已停止"
}

# 运行CLI测试
run_cli_tests() {
    log_info "运行CLI测试..."
    
    cd "$PROJECT_ROOT"
    
    if [ -f "tests/cli/run_cli_tests.py" ]; then
        python3 tests/cli/run_cli_tests.py \
            --output-file=$TEST_RESULTS_DIR/cli-results.json \
            || {
                log_error "CLI测试失败"
                return 1
            }
        
        log_success "CLI测试通过"
    else
        log_warning "未找到CLI测试脚本"
    fi
}

# 运行性能测试
run_performance_tests() {
    log_info "运行性能测试..."
    
    cd "$PROJECT_ROOT"
    
    if [ -d "tests/performance" ]; then
        python3 -m pytest tests/performance/ \
            --junit-xml=$TEST_RESULTS_DIR/performance-results.xml \
            --tb=short \
            -v \
            || {
                log_error "性能测试失败"
                return 1
            }
        
        log_success "性能测试通过"
    else
        log_warning "未找到性能测试目录"
    fi
}

# 运行安全测试
run_security_tests() {
    log_info "运行安全测试..."
    
    cd "$PROJECT_ROOT"
    
    # 检查依赖漏洞
    if command -v safety &> /dev/null; then
        safety check --json --output $TEST_RESULTS_DIR/security-deps.json || {
            log_warning "依赖安全检查发现问题"
        }
    else
        log_warning "safety 未安装，跳过依赖安全检查"
    fi
    
    # 静态代码安全分析
    if command -v bandit &> /dev/null; then
        bandit -r python/ -f json -o $TEST_RESULTS_DIR/security-code.json || {
            log_warning "代码安全分析发现问题"
        }
    else
        log_warning "bandit 未安装，跳过代码安全分析"
    fi
    
    log_success "安全测试完成"
}

# 代码质量检查
run_code_quality_checks() {
    log_info "运行代码质量检查..."
    
    cd "$PROJECT_ROOT"
    
    # pylint检查
    if command -v pylint &> /dev/null; then
        pylint python/ --output-format=json > $TEST_RESULTS_DIR/pylint-report.json 2>/dev/null || {
            log_warning "pylint 检查发现问题"
        }
    else
        log_warning "pylint 未安装，跳过代码质量检查"
    fi
    
    # flake8检查
    if command -v flake8 &> /dev/null; then
        flake8 python/ --format=json --output-file=$TEST_RESULTS_DIR/flake8-report.json || {
            log_warning "flake8 检查发现问题"
        }
    else
        log_warning "flake8 未安装，跳过风格检查"
    fi
    
    # mypy类型检查
    if command -v mypy &> /dev/null; then
        mypy python/ --json-report $TEST_RESULTS_DIR/mypy-report || {
            log_warning "mypy 类型检查发现问题"
        }
    else
        log_warning "mypy 未安装，跳过类型检查"
    fi
    
    log_success "代码质量检查完成"
}

# 生成测试报告
generate_test_report() {
    log_info "生成测试报告..."
    
    local start_time=$(date -d "$test_start_time" +%s)
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # 统计测试结果
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    local skipped_tests=0
    
    # 解析JUnit XML文件
    for xml_file in "$TEST_RESULTS_DIR"/*-results.xml; do
        if [ -f "$xml_file" ]; then
            local tests=$(grep -o 'tests="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
            local failures=$(grep -o 'failures="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
            local errors=$(grep -o 'errors="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
            local skipped=$(grep -o 'skipped="[0-9]*"' "$xml_file" | grep -o '[0-9]*' || echo "0")
            
            total_tests=$((total_tests + tests))
            failed_tests=$((failed_tests + failures + errors))
            skipped_tests=$((skipped_tests + skipped))
        fi
    done
    
    passed_tests=$((total_tests - failed_tests - skipped_tests))
    
    # 计算覆盖率
    local coverage_percentage="N/A"
    if [ -f "$COVERAGE_DIR/unit-coverage.xml" ]; then
        coverage_percentage=$(grep -o 'line-rate="[0-9.]*"' "$COVERAGE_DIR/unit-coverage.xml" | head -1 | grep -o '[0-9.]*' || echo "0")
        coverage_percentage=$(echo "$coverage_percentage * 100" | bc -l | cut -d. -f1)%
    fi
    
    # 生成JSON报告
    cat > "$REPORT_FILE" << EOF
{
    "test_run": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "duration_seconds": $duration,
        "environment": {
            "python_version": "$(python3 --version | cut -d' ' -f2)",
            "platform": "$(uname -s)",
            "architecture": "$(uname -m)"
        }
    },
    "summary": {
        "total_tests": $total_tests,
        "passed": $passed_tests,
        "failed": $failed_tests,
        "skipped": $skipped_tests,
        "success_rate": $(echo "scale=2; $passed_tests * 100 / $total_tests" | bc -l || echo "0"),
        "coverage": "$coverage_percentage"
    },
    "test_suites": {
        "unit_tests": {
            "status": "$([ -f "$TEST_RESULTS_DIR/unit-results.xml" ] && echo "completed" || echo "skipped")",
            "result_file": "unit-results.xml"
        },
        "integration_tests": {
            "status": "$([ -f "$TEST_RESULTS_DIR/integration-results.xml" ] && echo "completed" || echo "skipped")",
            "result_file": "integration-results.xml"
        },
        "cli_tests": {
            "status": "$([ -f "$TEST_RESULTS_DIR/cli-results.json" ] && echo "completed" || echo "skipped")",
            "result_file": "cli-results.json"
        },
        "performance_tests": {
            "status": "$([ -f "$TEST_RESULTS_DIR/performance-results.xml" ] && echo "completed" || echo "skipped")",
            "result_file": "performance-results.xml"
        }
    },
    "quality_checks": {
        "security": {
            "dependency_scan": "$([ -f "$TEST_RESULTS_DIR/security-deps.json" ] && echo "completed" || echo "skipped")",
            "code_scan": "$([ -f "$TEST_RESULTS_DIR/security-code.json" ] && echo "completed" || echo "skipped")"
        },
        "code_quality": {
            "pylint": "$([ -f "$TEST_RESULTS_DIR/pylint-report.json" ] && echo "completed" || echo "skipped")",
            "flake8": "$([ -f "$TEST_RESULTS_DIR/flake8-report.json" ] && echo "completed" || echo "skipped")",
            "mypy": "$([ -d "$TEST_RESULTS_DIR/mypy-report" ] && echo "completed" || echo "skipped")"
        }
    },
    "artifacts": {
        "coverage_html": "coverage/unit/index.html",
        "test_results": "test-results/",
        "logs": "logs/"
    }
}
EOF
    
    log_success "测试报告已生成: $REPORT_FILE"
}

# 显示测试摘要
show_test_summary() {
    log_info "测试执行摘要："
    echo "============================================"
    
    if [ -f "$REPORT_FILE" ]; then
        local total=$(jq -r '.summary.total_tests' "$REPORT_FILE")
        local passed=$(jq -r '.summary.passed' "$REPORT_FILE")
        local failed=$(jq -r '.summary.failed' "$REPORT_FILE")
        local skipped=$(jq -r '.summary.skipped' "$REPORT_FILE")
        local coverage=$(jq -r '.summary.coverage' "$REPORT_FILE")
        local success_rate=$(jq -r '.summary.success_rate' "$REPORT_FILE")
        
        echo "总测试数量: $total"
        echo "通过测试: $passed"
        echo "失败测试: $failed"
        echo "跳过测试: $skipped"
        echo "成功率: $success_rate%"
        echo "代码覆盖率: $coverage"
        echo ""
        
        if [ "$failed" -gt 0 ]; then
            log_error "有 $failed 个测试失败"
            echo "详细信息请查看: $TEST_RESULTS_DIR/"
        else
            log_success "所有测试通过！"
        fi
    else
        log_warning "测试报告文件不存在"
    fi
    
    echo "============================================"
    echo "测试结果位置: $TEST_RESULTS_DIR"
    echo "覆盖率报告: $COVERAGE_DIR/unit/index.html"
    echo "详细报告: $REPORT_FILE"
}

# 清理测试环境
cleanup_test_environment() {
    log_info "清理测试环境..."
    
    # 停止可能残留的进程
    pkill -f "python.*main.py" 2>/dev/null || true
    
    # 恢复原始环境文件
    if [ -f "$PROJECT_ROOT/.env.backup" ]; then
        mv "$PROJECT_ROOT/.env.backup" "$PROJECT_ROOT/.env"
    fi
    
    # 清理临时文件
    rm -rf "$PROJECT_ROOT/test-data" 2>/dev/null || true
    
    log_success "测试环境清理完成"
}

# 主测试流程
run_all_tests() {
    local test_start_time=$(date)
    
    # 检查是否只运行特定测试
    local run_unit=${RUN_UNIT_TESTS:-true}
    local run_integration=${RUN_INTEGRATION_TESTS:-true}
    local run_cli=${RUN_CLI_TESTS:-true}
    local run_performance=${RUN_PERFORMANCE_TESTS:-true}
    local run_security=${RUN_SECURITY_TESTS:-true}
    local run_quality=${RUN_QUALITY_CHECKS:-true}
    
    # 运行测试套件
    if [ "$run_unit" = "true" ]; then
        run_unit_tests || return 1
    fi
    
    if [ "$run_integration" = "true" ]; then
        run_integration_tests || return 1
    fi
    
    if [ "$run_cli" = "true" ]; then
        run_cli_tests || return 1
    fi
    
    if [ "$run_performance" = "true" ]; then
        run_performance_tests || return 1
    fi
    
    if [ "$run_security" = "true" ]; then
        run_security_tests
    fi
    
    if [ "$run_quality" = "true" ]; then
        run_code_quality_checks
    fi
    
    # 生成报告
    generate_test_report
    show_test_summary
    
    return 0
}

# 主函数
main() {
    local action=${1:-all}
    
    case $action in
        "all")
            check_prerequisites
            setup_test_environment
            run_all_tests
            cleanup_test_environment
            ;;
        "unit")
            check_prerequisites
            setup_test_environment
            run_unit_tests
            cleanup_test_environment
            ;;
        "integration")
            check_prerequisites
            setup_test_environment
            run_integration_tests
            cleanup_test_environment
            ;;
        "cli")
            check_prerequisites
            setup_test_environment
            run_cli_tests
            cleanup_test_environment
            ;;
        "performance")
            check_prerequisites
            setup_test_environment
            run_performance_tests
            cleanup_test_environment
            ;;
        "security")
            check_prerequisites
            setup_test_environment
            run_security_tests
            cleanup_test_environment
            ;;
        "quality")
            check_prerequisites
            setup_test_environment
            run_code_quality_checks
            cleanup_test_environment
            ;;
        "report")
            if [ -f "$REPORT_FILE" ]; then
                show_test_summary
            else
                log_error "测试报告不存在，请先运行测试"
                exit 1
            fi
            ;;
        "clean")
            rm -rf "$TEST_RESULTS_DIR" "$COVERAGE_DIR"
            log_success "测试结果已清理"
            ;;
        *)
            echo "用法: $0 [all|unit|integration|cli|performance|security|quality|report|clean]"
            echo ""
            echo "命令说明："
            echo "  all          - 运行所有测试（默认）"
            echo "  unit         - 只运行单元测试"
            echo "  integration  - 只运行集成测试"
            echo "  cli          - 只运行CLI测试"
            echo "  performance  - 只运行性能测试"
            echo "  security     - 只运行安全测试"
            echo "  quality      - 只运行代码质量检查"
            echo "  report       - 显示测试报告"
            echo "  clean        - 清理测试结果"
            echo ""
            echo "环境变量："
            echo "  RUN_UNIT_TESTS=false         - 跳过单元测试"
            echo "  RUN_INTEGRATION_TESTS=false  - 跳过集成测试"
            echo "  RUN_CLI_TESTS=false          - 跳过CLI测试"
            echo "  RUN_PERFORMANCE_TESTS=false  - 跳过性能测试"
            echo "  RUN_SECURITY_TESTS=false     - 跳过安全测试"
            echo "  RUN_QUALITY_CHECKS=false     - 跳过质量检查"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"