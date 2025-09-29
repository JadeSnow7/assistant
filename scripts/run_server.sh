#!/bin/bash

# HuShell 增强服务启动脚本
set -e

# 脚本版本和信息
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="HuShell 服务启动脚本"

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
log_debug() { [ "$DEBUG_MODE" = "true" ] && echo -e "${PURPLE}🐛${NC} $1"; }

echo -e "${CYAN}🚀 启动HuShell服务...${NC}"

# 默认配置
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_GRPC_PORT="50051"
DEFAULT_LOG_LEVEL="INFO"
DEFAULT_WORKERS="4"

# 配置变量
HOST=${HOST:-$DEFAULT_HOST}
PORT=${PORT:-$DEFAULT_PORT}
GRPC_PORT=${GRPC_PORT:-$DEFAULT_GRPC_PORT}
LOG_LEVEL=${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}
DEBUG=${DEBUG:-false}
WORKERS=${WORKERS:-$DEFAULT_WORKERS}

# 服务管理变量
GRPC_PID=""
API_PID=""
START_TIME=""
DEBUG_MODE=false
VERBOSE=false
FORCE_RESTART=false
HEALTH_CHECK_TIMEOUT=30
SERVICE_STARTUP_WAIT=5

# PID文件路径
PID_DIR="./run"
GRPC_PID_FILE="$PID_DIR/grpc.pid"
API_PID_FILE="$PID_DIR/api.pid"

# 检查服务状态和端口占用
check_service_status() {
    local port=$1
    local service_name="$2"
    local pid_file="$3"
    
    log_debug "检查端口 $port 的状态 ($service_name)"
    
    # 检查端口占用
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local existing_pid=$(lsof -Pi :$port -sTCP:LISTEN -t | head -1)
        log_warning "端口 $port 已被占用 ($service_name, PID: $existing_pid)"
        
        # 检查是否是我们的服务
        if [ -f "$pid_file" ]; then
            local recorded_pid=$(cat "$pid_file" 2>/dev/null || echo "")
            if [ "$existing_pid" = "$recorded_pid" ]; then
                log_info "发现已运行的服务实例 (PID: $existing_pid)"
                if [ "$FORCE_RESTART" = "true" ]; then
                    log_warning "强制重启模式，关闭现有服务..."
                    stop_service_by_pid "$existing_pid" "$service_name"
                    return 0
                else
                    log_error "服务已在运行，使用 --force 参数强制重启"
                    return 1
                fi
            fi
        fi
        
        # 非我们的服务占用端口
        if [ "$FORCE_RESTART" = "true" ]; then
            log_warning "强制关闭占用端口的进程..."
            stop_service_by_pid "$existing_pid" "unknown"
        else
            read -p "是否要停止现有服务并重启？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                stop_service_by_pid "$existing_pid" "unknown"
            else
                log_error "取消启动"
                return 1
            fi
        fi
    fi
    
    return 0
}

# 按PID停止服务
stop_service_by_pid() {
    local pid="$1"
    local service_name="$2"
    
    if [ -z "$pid" ]; then
        return 0
    fi
    
    log_info "正在停止服务 $service_name (PID: $pid)..."
    
    # 发送SIGTERM
    if kill -TERM "$pid" 2>/dev/null; then
        # 等待服务优雅关闭
        local wait_count=0
        while [ $wait_count -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
            sleep 1
            wait_count=$((wait_count + 1))
        done
        
        # 如果仍在运行，强制杀死
        if kill -0 "$pid" 2>/dev/null; then
            log_warning "服务未优雅关闭，强制终止..."
            kill -KILL "$pid" 2>/dev/null || true
        fi
        
        log_success "服务 $service_name 已停止"
    else
        log_warning "无法停止服务 $service_name (PID: $pid)"
    fi
}

# 启动C++后端服务
start_cpp_backend() {
    log_info "启动C++后端服务..."
    
    # 检查端口
    if ! check_service_status $GRPC_PORT "ai_assistant_server" "$GRPC_PID_FILE"; then
        return 1
    fi
    
    # 准备启动参数
    local cpp_args=(
        "--port=$GRPC_PORT"
        "--log-level=$LOG_LEVEL"
    )
    
    if [ "$DEBUG_MODE" = "true" ]; then
        cpp_args+=("--debug")
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        cpp_args+=("--verbose")
    fi
    
    # 启动服务
    log_info "在端口 $GRPC_PORT 启动gRPC服务..."
    log_debug "C++启动参数: ${cpp_args[*]}"
    
    nohup "$CPP_EXECUTABLE" "${cpp_args[@]}" \
        > logs/grpc_server.log 2>&1 &
    
    GRPC_PID=$!
    echo "$GRPC_PID" > "$GRPC_PID_FILE"
    log_success "gRPC服务已启动 (PID: $GRPC_PID)"
    
    # 等待服务启动
    log_info "等待服务启动 ($SERVICE_STARTUP_WAIT 秒)..."
    sleep $SERVICE_STARTUP_WAIT
    
    # 验证服务状态
    if ! kill -0 $GRPC_PID 2>/dev/null; then
        log_error "gRPC服务启动失败，请查看日志: logs/grpc_server.log"
        rm -f "$GRPC_PID_FILE"
        return 1
    fi
    
    # 测试gRPC连接
    if command -v grpc_health_probe &> /dev/null; then
        if ! grpc_health_probe -addr=localhost:$GRPC_PORT -connect-timeout=5s; then
            log_warning "gRPC健康检查失败，但进程仍在运行"
        fi
    else
        # 简单的端口连接测试
        if ! timeout 5 nc -z localhost $GRPC_PORT 2>/dev/null; then
            log_warning "gRPC端口连接测试失败"
        fi
    fi
    
    return 0
}

# 启动Python API服务
start_python_api() {
    echo "🐍 启动Python API服务..."
    
    # 检查端口
    check_service_status $PORT "python.*main.py"
    
    # 进入Python目录
    cd python
    
    # 检查依赖
    if ! python3 -c "import fastapi" 2>/dev/null; then
        echo "❌ Python依赖未安装，请先运行构建脚本"
        echo "   运行: ./scripts/build.sh"
        exit 1
    fi
    
    # 设置环境变量
    export GRPC_SERVER_ADDRESS="localhost:$GRPC_PORT"
    export HOST=$HOST
    export PORT=$PORT
    export DEBUG=$DEBUG
    export LOG_LEVEL=$LOG_LEVEL
    
    # 启动服务
    echo "🌐 在 http://$HOST:$PORT 启动API服务..."
    
    if [ "$DEBUG" = "true" ]; then
        # 开发模式 - 前台运行带热重载
        uvicorn main:app \
            --host $HOST \
            --port $PORT \
            --reload \
            --log-level $(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]')
    else
        # 生产模式 - 后台运行
        nohup uvicorn main:app \
            --host $HOST \
            --port $PORT \
            --workers 4 \
            --log-level $(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]') \
            > ../logs/api_server.log 2>&1 &
        
        API_PID=$!
        echo "✅ API服务已启动 (PID: $API_PID)"
        
        # 等待服务启动
        sleep 3
        
        # 验证服务
        if ! kill -0 $API_PID 2>/dev/null; then
            echo "❌ API服务启动失败，请查看日志: logs/api_server.log"
            exit 1
        fi
    fi
    
    cd ..
}

# 创建必要的目录
setup_directories() {
    log_info "创建必要目录..."
    
    local directories=("logs" "data" "src/plugins" "run" "tmp")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_debug "创建目录: $dir"
        fi
    done
    
    # 设置正确的权限
    chmod 755 logs data run tmp 2>/dev/null || true
    
    log_success "目录创建完成"
}

# 增强健康检查
health_check() {
    log_info "执行增强健康检查..."
    
    local health_results=()
    local overall_health=true
    
    # 检查gRPC服务
    log_debug "检查gRPC服务健康状态..."
    if timeout $HEALTH_CHECK_TIMEOUT nc -z localhost $GRPC_PORT 2>/dev/null; then
        health_results+=("gRPC服务: 健康")
        log_success "gRPC服务健康检查通过"
    else
        health_results+=("gRPC服务: 异常")
        log_error "gRPC服务健康检查失败"
        overall_health=false
    fi
    
    # 检查API服务
    log_debug "检查API服务健康状态..."
    local api_health_url="http://localhost:$PORT/health"
    
    if timeout $HEALTH_CHECK_TIMEOUT curl -sf "$api_health_url" >/dev/null 2>&1; then
        health_results+=("API服务: 健康")
        log_success "API服务健康检查通过"
        
        # 获取详细健康信息
        local health_info
        if health_info=$(timeout 10 curl -s "$api_health_url" 2>/dev/null); then
            log_debug "API健康信息: $health_info"
        fi
    else
        health_results+=("API服务: 异常")
        log_error "API服务健康检查失败"
        overall_health=false
    fi
    
    # 检查系统资源
    check_system_resources
    
    # 显示健康检查摘要
    display_health_summary "${health_results[@]}"
    
    if [ "$overall_health" = "true" ]; then
        log_success "所有服务健康检查通过"
        return 0
    else
        log_error "健康检查失败，请检查服务状态"
        return 1
    fi
}

# 检查系统资源
check_system_resources() {
    log_debug "检查系统资源使用情况..."
    
    # 检查内存使用率
    if command -v free &> /dev/null; then
        local mem_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2 }')
        log_debug "内存使用率: ${mem_usage}%"
        
        if (( $(echo "$mem_usage > 90" | bc -l 2>/dev/null || echo 0) )); then
            log_warning "内存使用率较高: ${mem_usage}%"
        fi
    fi
    
    # 检查磁盘空间
    if command -v df &> /dev/null; then
        local disk_usage=$(df . | awk 'NR==2{print $5}' | sed 's/%//')
        log_debug "磁盘使用率: ${disk_usage}%"
        
        if [ "$disk_usage" -gt 90 ]; then
            log_warning "磁盘空间不足: ${disk_usage}%"
        fi
    fi
}

# 显示健康检查摘要
display_health_summary() {
    echo
    echo -e "${CYAN}🌡️ 健康检查摘要${NC}"
    echo "=================="
    for result in "$@"; do
        if [[ $result == *"健康"* ]]; then
            echo -e "${GREEN}✅ $result${NC}"
        else
            echo -e "${RED}❌ $result${NC}"
        fi
    done
    echo
}

# 显示服务信息
show_service_info() {
    echo ""
    echo "🎉 HuShell 服务启动成功！"
    echo "================================"
    echo "📡 gRPC服务:   localhost:$GRPC_PORT"
    echo "🌐 API服务:    http://$HOST:$PORT"
    echo "📊 健康检查:   http://$HOST:$PORT/health"
    echo "📖 API文档:    http://$HOST:$PORT/docs"
    echo "📋 日志目录:   ./logs/"
    echo ""
    echo "🔧 管理命令:"
    echo "   查看日志:   tail -f logs/api_server.log"
    echo "   停止服务:   ./scripts/stop_server.sh"
    echo "   重启服务:   ./scripts/restart_server.sh"
    echo ""
}

# 信号处理
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    
    # 停止API服务
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    
    # 停止gRPC服务
    if [ ! -z "$GRPC_PID" ]; then
        kill $GRPC_PID 2>/dev/null || true
    fi
    
    echo "✅ 服务已停止"
    exit 0
}

# 显示服务配置
show_service_config() {
    echo
    echo -e "${CYAN}📋 服务配置${NC}"
    echo "=================="
    echo "API主机: $HOST"
    echo "API端口: $PORT"
    echo "gRPC端口: $GRPC_PORT"
    echo "工作进程: $WORKERS"
    echo "日志级别: $LOG_LEVEL"
    echo "调试模式: $([ "$DEBUG" = "true" ] && echo "是" || echo "否")"
    echo "详细输出: $([ "$VERBOSE" = "true" ] && echo "是" || echo "否")"
    echo "强制重启: $([ "$FORCE_RESTART" = "true" ] && echo "是" || echo "否")"
    echo
}

# 错误处理函数
handle_error() {
    local exit_code=$?
    local line_number=$1
    
    log_error "服务启动失败 (退出码: $exit_code, 行号: $line_number)"
    
    if [ "$DEBUG_MODE" = "true" ]; then
        echo -e "${RED}调试信息:${NC}"
        echo "  - 脚本: $0"
        echo "  - 行号: $line_number"
        echo "  - 退出码: $exit_code"
        echo "  - 当前目录: $(pwd)"
    fi
    
    log_info "可能的解决方案:"
    echo "  1. 检查日志文件: logs/grpc_server.log, logs/api_server.log"
    echo "  2. 检查端口占用: lsof -i :$PORT -i :$GRPC_PORT"
    echo "  3. 检查依赖安装: ./scripts/build.sh --skip-tests"
    echo "  4. 使用 --debug --verbose 获取更多信息"
    
    cleanup
    exit $exit_code
}

# 显示帮助信息
show_help() {
    cat << EOF
${SCRIPT_NAME} v${SCRIPT_VERSION}
使用方法: $0 [选项]

服务配置:
  --host HOST          API服务主机 [默认: $DEFAULT_HOST]
  --port PORT          API服务端口 [默认: $DEFAULT_PORT]
  --grpc-port PORT     gRPC服务端口 [默认: $DEFAULT_GRPC_PORT]
  --workers N          uvicorn工作进程数 [默认: $DEFAULT_WORKERS]
  --log-level LEVEL    日志级别 [默认: $DEFAULT_LOG_LEVEL]
  
运行模式:
  --debug              启用调试模式 (前台运行，热重载)
  --force              强制重启，停止占用端口的进程
  
监控选项:
  --verbose            详细输出
  --health-timeout N   健康检查超时时间(秒) [默认: 30]
  --startup-wait N     服务启动等待时间(秒) [默认: 5]
  
其他选项:
  --help               显示此帮助信息
  --version            显示版本信息
  
示例:
  $0                           # 标准启动
  $0 --debug                   # 调试模式
  $0 --port 8080 --workers 8   # 自定义端口和工作进程
  $0 --force --verbose         # 强制重启，详细输出
EOF
}

# 显示版本信息
show_version() {
    echo "${SCRIPT_NAME} v${SCRIPT_VERSION}"
    echo "支持的服务: gRPC后端, FastAPI前端"
    echo "支持的部署模式: 开发模式, 生产模式"
}

# 解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                HOST="$2"
                shift 2
                ;;
            --port)
                PORT="$2"
                shift 2
                ;;
            --grpc-port)
                GRPC_PORT="$2"
                shift 2
                ;;
            --workers)
                WORKERS="$2"
                shift 2
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            --health-timeout)
                HEALTH_CHECK_TIMEOUT="$2"
                shift 2
                ;;
            --startup-wait)
                SERVICE_STARTUP_WAIT="$2"
                shift 2
                ;;
            --debug)
                DEBUG=true
                DEBUG_MODE=true
                shift
                ;;
            --force)
                FORCE_RESTART=true
                shift
                ;;
            --verbose)
                VERBOSE=true
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
    if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
        log_error "无效的API端口: $PORT"
        exit 1
    fi
    
    if ! [[ "$GRPC_PORT" =~ ^[0-9]+$ ]] || [ "$GRPC_PORT" -lt 1024 ] || [ "$GRPC_PORT" -gt 65535 ]; then
        log_error "无效的gRPC端口: $GRPC_PORT"
        exit 1
    fi
    
    if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [ "$WORKERS" -le 0 ]; then
        log_error "无效的工作进程数: $WORKERS"
        exit 1
    fi
}

# 主函数
main() {
    echo -e "${CYAN}${SCRIPT_NAME} v${SCRIPT_VERSION}${NC}"
    echo "==============================================="
    
    # 记录开始时间
    START_TIME=$(date +%s)
    
    # 解析参数
    parse_arguments "$@"
    
    # 显示配置
    show_service_config
    
    # 设置错误处理
    trap 'handle_error $LINENO' ERR
    trap cleanup SIGINT SIGTERM
    
    # 检查构建产物和依赖
    check_build_artifacts || exit 1
    
    # 执行启动步骤
    setup_directories
    start_cpp_backend || exit 1
    start_python_api || exit 1
    
    # 等待服务完全启动
    log_info "等待服务完全启动..."
    sleep $SERVICE_STARTUP_WAIT
    
    # 执行健康检查
    if health_check; then
        # 计算启动时间
        local end_time=$(date +%s)
        local startup_time=$((end_time - START_TIME))
        
        # 显示服务信息
        show_service_info "$startup_time"
        
        if [ "$DEBUG" = "false" ]; then
            log_info "服务在后台运行，按 Ctrl+C 停止服务"
            # 等待信号
            while true; do
                sleep 1
            done
        fi
    else
        log_error "服务启动失败，请检查日志"
        cleanup
        exit 1
    fi
}

main "$@"
main "$@"