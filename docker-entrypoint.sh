#!/bin/bash
set -e

# AI Assistant Docker入口脚本

# 默认配置
DEFAULT_HOST=${HOST:-0.0.0.0}
DEFAULT_PORT=${PORT:-8000}
DEFAULT_GRPC_PORT=${GRPC_PORT:-50051}
DEFAULT_LOG_LEVEL=${LOG_LEVEL:-INFO}
DEFAULT_WORKERS=${WORKERS:-4}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✅${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }

# 显示帮助
show_help() {
    cat << EOF
AI Assistant Docker容器

用法: 
  docker run [docker选项] ai-assistant [命令] [选项]

命令:
  server          启动完整服务器 (默认)
  cli             启动CLI模式
  api-only        仅启动API服务
  grpc-only       仅启动gRPC服务
  health-check    执行健康检查
  version         显示版本信息
  help            显示此帮助

环境变量:
  HOST            API服务绑定地址 (默认: 0.0.0.0)
  PORT            API服务端口 (默认: 8000)
  GRPC_PORT       gRPC服务端口 (默认: 50051)
  LOG_LEVEL       日志级别 (默认: INFO)
  WORKERS         API服务工作进程数 (默认: 4)
  DEBUG           调试模式 (默认: false)

示例:
  # 启动完整服务
  docker run -p 8000:8000 -p 50051:50051 ai-assistant

  # 启动调试模式
  docker run -e DEBUG=true -p 8000:8000 ai-assistant

  # 仅启动API服务
  docker run -p 8000:8000 ai-assistant api-only

  # 启动CLI模式
  docker run -it ai-assistant cli
EOF
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查gRPC服务
    if nc -z localhost ${DEFAULT_GRPC_PORT} 2>/dev/null; then
        log_success "gRPC服务 (端口 ${DEFAULT_GRPC_PORT}) 正常"
    else
        log_error "gRPC服务不可达"
        return 1
    fi
    
    # 检查API服务
    if curl -sf http://localhost:${DEFAULT_PORT}/health >/dev/null 2>&1; then
        log_success "API服务 (端口 ${DEFAULT_PORT}) 正常"
    else
        log_error "API服务不可达"
        return 1
    fi
    
    log_success "所有服务健康检查通过"
    return 0
}

# 等待服务启动
wait_for_services() {
    local max_attempts=30
    local attempt=1
    
    log_info "等待服务启动..."
    
    while [ $attempt -le $max_attempts ]; do
        if health_check >/dev/null 2>&1; then
            log_success "服务启动完成"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "服务启动超时"
    return 1
}

# 启动gRPC服务
start_grpc_service() {
    log_info "启动gRPC服务..."
    
    if [ -f "/app/install/bin/ai_assistant_server" ]; then
        /app/install/bin/ai_assistant_server \
            --port=${DEFAULT_GRPC_PORT} \
            --log-level=${DEFAULT_LOG_LEVEL} &
        
        GRPC_PID=$!
        echo $GRPC_PID > /app/run/grpc.pid
        log_success "gRPC服务已启动 (PID: $GRPC_PID)"
    else
        log_error "gRPC服务可执行文件未找到"
        return 1
    fi
}

# 启动API服务
start_api_service() {
    log_info "启动API服务..."
    
    cd /app/python
    
    # 设置环境变量
    export GRPC_SERVER_ADDRESS="localhost:${DEFAULT_GRPC_PORT}"
    export HOST=${DEFAULT_HOST}
    export PORT=${DEFAULT_PORT}
    export LOG_LEVEL=${DEFAULT_LOG_LEVEL}
    
    if [ "${DEBUG}" = "true" ]; then
        # 调试模式
        log_info "启动调试模式API服务..."
        uvicorn main:app \
            --host ${DEFAULT_HOST} \
            --port ${DEFAULT_PORT} \
            --reload \
            --log-level $(echo ${DEFAULT_LOG_LEVEL} | tr '[:upper:]' '[:lower:]') &
    else
        # 生产模式
        log_info "启动生产模式API服务..."
        uvicorn main:app \
            --host ${DEFAULT_HOST} \
            --port ${DEFAULT_PORT} \
            --workers ${DEFAULT_WORKERS} \
            --log-level $(echo ${DEFAULT_LOG_LEVEL} | tr '[:upper:]' '[:lower:]') &
    fi
    
    API_PID=$!
    echo $API_PID > /app/run/api.pid
    log_success "API服务已启动 (PID: $API_PID)"
    
    cd /app
}

# 启动CLI模式
start_cli() {
    log_info "启动CLI模式..."
    
    # 检查是否为交互式终端
    if [ -t 0 ]; then
        python3 start_cli.py
    else
        log_warning "非交互式终端，启动简单CLI模式"
        python3 -c "
import asyncio
from ui.shared.ai_client import EnhancedAIClient

async def simple_chat():
    client = EnhancedAIClient()
    print('AI Assistant CLI (非交互模式)')
    print('输入消息并按回车，输入 quit 退出')
    
    while True:
        try:
            message = input('> ')
            if message.lower() in ['quit', 'exit']:
                break
            result = await client.chat(message)
            print(f'AI: {result.get(\"content\", \"无响应\")}')
        except (EOFError, KeyboardInterrupt):
            break
    
    await client.cleanup()
    print('再见!')

asyncio.run(simple_chat())
"
    fi
}

# 清理函数
cleanup() {
    log_info "正在停止服务..."
    
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
    
    log_success "服务已停止"
}

# 设置信号处理
trap cleanup SIGTERM SIGINT

# 主函数
main() {
    local command=${1:-server}
    
    case $command in
        server)
            log_info "启动AI Assistant服务器..."
            start_grpc_service
            sleep 3
            start_api_service
            sleep 5
            
            if wait_for_services; then
                log_success "AI Assistant服务器启动成功!"
                log_info "API服务: http://localhost:${DEFAULT_PORT}"
                log_info "gRPC服务: localhost:${DEFAULT_GRPC_PORT}"
                log_info "API文档: http://localhost:${DEFAULT_PORT}/docs"
                log_info "健康检查: http://localhost:${DEFAULT_PORT}/health"
                
                # 保持容器运行
                wait
            else
                log_error "服务启动失败"
                cleanup
                exit 1
            fi
            ;;
            
        cli)
            start_cli
            ;;
            
        api-only)
            log_info "仅启动API服务..."
            start_api_service
            wait
            ;;
            
        grpc-only)
            log_info "仅启动gRPC服务..."
            start_grpc_service
            wait
            ;;
            
        health-check)
            health_check
            ;;
            
        version)
            echo "AI Assistant Docker Container"
            echo "Version: $(cat /app/python/core/config.py | grep 'version:' | cut -d'"' -f2 || echo 'unknown')"
            echo "Build: $(date)"
            ;;
            
        help)
            show_help
            ;;
            
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"