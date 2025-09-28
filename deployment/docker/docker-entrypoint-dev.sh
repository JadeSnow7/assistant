#!/bin/bash
set -e

# AI Assistant 开发环境Docker入口脚本

# 默认配置
DEFAULT_HOST=${HOST:-0.0.0.0}
DEFAULT_PORT=${PORT:-8000}
DEFAULT_GRPC_PORT=${GRPC_PORT:-50051}
DEFAULT_LOG_LEVEL=${LOG_LEVEL:-DEBUG}
DEFAULT_WORKERS=${WORKERS:-1}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✅${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }
log_debug() { echo -e "${PURPLE}🐛${NC} $1"; }

# 开发环境欢迎信息
show_dev_welcome() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ___    ____   ___                _       __              __ 
   /   |  /  _/  /   |  __________(_)_____/ /_____ _____  / /_
  / /| |  / /   / /| | / ___/ ___/ / ___/ __/ ___/ / __ \/ __/
 / ___ |_/ /   / ___ |(__  |__  ) (__  ) /_/ /__/ / / / / /_  
/_/  |_/___/  /_/  |_/____/____/_/____/\__/\___/_/_/ /_/\__/  
                                                              
         🚀 开发环境 - Development Environment 🚀
EOF
    echo -e "${NC}"
    echo -e "${GREEN}欢迎使用AI Assistant开发环境！${NC}"
    echo ""
    echo -e "${YELLOW}可用命令:${NC}"
    echo "  server      - 启动开发服务器 (热重载)"
    echo "  cli         - 启动CLI开发模式"
    echo "  test        - 运行测试套件"
    echo "  quality     - 代码质量检查"
    echo "  debug       - 启动调试服务器"
    echo "  shell       - 进入开发Shell"
    echo "  build       - 重新构建C++组件"
    echo ""
}

# 启动开发服务器
start_dev_server() {
    log_info "启动AI Assistant开发服务器..."
    
    # 启动gRPC服务
    if [ -f "/app/install/bin/ai_assistant_server" ]; then
        log_info "启动gRPC开发服务 (端口: ${DEFAULT_GRPC_PORT})..."
        /app/install/bin/ai_assistant_server \
            --port=${DEFAULT_GRPC_PORT} \
            --log-level=${DEFAULT_LOG_LEVEL} \
            --debug &
        
        GRPC_PID=$!
        echo $GRPC_PID > /app/run/grpc.pid
        log_success "gRPC服务已启动 (PID: $GRPC_PID)"
    else
        log_warning "gRPC服务未找到，将仅启动API服务"
    fi
    
    sleep 2
    
    # 启动API开发服务
    log_info "启动API开发服务 (端口: ${DEFAULT_PORT})..."
    cd /app/python
    
    export GRPC_SERVER_ADDRESS="localhost:${DEFAULT_GRPC_PORT}"
    export HOST=${DEFAULT_HOST}
    export PORT=${DEFAULT_PORT}
    export LOG_LEVEL=${DEFAULT_LOG_LEVEL}
    export DEBUG=true
    
    # 使用uvicorn的开发模式，支持热重载
    uvicorn main:app \
        --host ${DEFAULT_HOST} \
        --port ${DEFAULT_PORT} \
        --reload \
        --reload-dir /app/python \
        --reload-dir /app/ui \
        --log-level $(echo ${DEFAULT_LOG_LEVEL} | tr '[:upper:]' '[:lower:]') &
    
    API_PID=$!
    echo $API_PID > /app/run/api.pid
    log_success "API开发服务已启动 (PID: $API_PID)"
    
    cd /app
    
    # 显示开发信息
    echo ""
    log_success "🎉 开发服务启动完成！"
    echo ""
    echo -e "${CYAN}📍 服务地址:${NC}"
    echo "  🌐 API服务:    http://localhost:${DEFAULT_PORT}"
    echo "  📡 gRPC服务:   localhost:${DEFAULT_GRPC_PORT}"
    echo "  📚 API文档:    http://localhost:${DEFAULT_PORT}/docs"
    echo "  🏥 健康检查:   http://localhost:${DEFAULT_PORT}/health"
    echo ""
    echo -e "${CYAN}🛠️ 开发工具:${NC}"
    echo "  📊 监控面板:   http://localhost:${DEFAULT_PORT}/monitor"
    echo "  🐛 调试端口:   5678 (Python debugpy)"
    echo ""
    echo -e "${CYAN}💡 开发提示:${NC}"
    echo "  - 代码更改会自动重载"
    echo "  - 日志文件: /app/logs/"
    echo "  - 配置文件: /app/.env"
    echo "  - 测试命令: python tests/cli/run_cli_tests.py"
    echo ""
}

# 启动调试服务器
start_debug_server() {
    log_info "启动调试服务器..."
    
    # 启动Python远程调试
    python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client src/main.py
}

# 运行测试
run_tests() {
    log_info "运行测试套件..."
    
    echo -e "${YELLOW}选择测试类型:${NC}"
    echo "1. 单元测试"
    echo "2. 集成测试"
    echo "3. CLI测试"
    echo "4. 性能测试"
    echo "5. 完整测试"
    
    read -p "请选择 (1-5): " choice
    
    case $choice in
        1)
            pytest tests/unit/ -v --cov=python
            ;;
        2)
            pytest tests/integration/ -v
            ;;
        3)
            python tests/cli/run_cli_tests.py --no-health-check
            ;;
        4)
            python tests/cli/run_cli_tests.py --no-health-check --suites performance
            ;;
        5)
            python tests/cli/run_cli_tests.py --no-health-check --suites commands display performance compatibility
            ;;
        *)
            log_error "无效选择"
            exit 1
            ;;
    esac
}

# 代码质量检查
check_code_quality() {
    log_info "执行代码质量检查..."
    
    echo -e "${YELLOW}🔍 Running Black (代码格式化)...${NC}"
    black --check --diff src/ ui/ || {
        echo -e "${RED}❌ Black检查失败，运行 'black src/ ui/' 修复${NC}"
        return 1
    }
    
    echo -e "${YELLOW}🔍 Running isort (导入排序)...${NC}"
    isort --check-only --diff src/ ui/ || {
        echo -e "${RED}❌ isort检查失败，运行 'isort src/ ui/' 修复${NC}"
        return 1
    }
    
    echo -e "${YELLOW}🔍 Running flake8 (代码规范)...${NC}"
    flake8 src/ ui/ --max-line-length=120 --extend-ignore=E203,W503 || {
        echo -e "${RED}❌ flake8检查失败${NC}"
        return 1
    }
    
    echo -e "${YELLOW}🔍 Running mypy (类型检查)...${NC}"
    mypy src/ --ignore-missing-imports || {
        echo -e "${RED}❌ mypy检查失败${NC}"
        return 1
    }
    
    log_success "✅ 所有代码质量检查通过！"
}

# 重新构建C++组件
rebuild_cpp() {
    log_info "重新构建C++组件..."
    
    cd /app
    rm -rf build
    mkdir build
    cd build
    
    cmake .. -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTS=ON
    cmake --build . --config Debug
    cmake --install . --prefix /app/install
    
    cd /app
    log_success "C++组件重新构建完成"
}

# 开发Shell
dev_shell() {
    log_info "进入开发Shell..."
    
    # 设置开发环境变量
    export PYTHONPATH="/app:/app/python"
    export PATH="/app/install/bin:$PATH"
    
    echo -e "${GREEN}开发环境已准备就绪！${NC}"
    echo ""
    echo -e "${YELLOW}可用别名:${NC}"
    echo "  serve  - 启动服务"
    echo "  test   - 运行测试"
    echo "  pytest - 运行pytest"
    echo ""
    
    exec /bin/bash
}

# 清理函数
cleanup() {
    log_info "正在停止开发服务..."
    
    # 停止API服务
    if [ -f "/app/run/api.pid" ]; then
        API_PID=$(cat /app/run/api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            kill -TERM $API_PID
            wait $API_PID 2>/dev/null || true
        fi
        rm -f /app/run/api.pid
    fi
    
    # 停止gRPC服务
    if [ -f "/app/run/grpc.pid" ]; then
        GRPC_PID=$(cat /app/run/grpc.pid)
        if kill -0 $GRPC_PID 2>/dev/null; then
            kill -TERM $GRPC_PID
            wait $GRPC_PID 2>/dev/null || true
        fi
        rm -f /app/run/grpc.pid
    fi
    
    log_success "开发服务已停止"
}

# 设置信号处理
trap cleanup SIGTERM SIGINT

# 主函数
main() {
    local command=${1:-server}
    
    # 显示欢迎信息
    if [ "$command" != "shell" ]; then
        show_dev_welcome
    fi
    
    case $command in
        server)
            start_dev_server
            # 保持容器运行
            wait
            ;;
            
        cli)
            log_info "启动CLI开发模式..."
            python3 ui/cli/modern_cli.py --debug
            ;;
            
        test)
            run_tests
            ;;
            
        quality)
            check_code_quality
            ;;
            
        debug)
            start_debug_server
            ;;
            
        shell)
            dev_shell
            ;;
            
        build)
            rebuild_cpp
            ;;
            
        *)
            log_error "未知命令: $command"
            echo ""
            echo -e "${YELLOW}可用命令:${NC}"
            echo "  server, cli, test, quality, debug, shell, build"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"