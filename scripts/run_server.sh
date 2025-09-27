#!/bin/bash

# AI Assistant 服务启动脚本
set -e

echo "🚀 启动AI Assistant服务..."

# 默认配置
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_GRPC_PORT="50051"
DEFAULT_LOG_LEVEL="INFO"

# 配置变量
HOST=${HOST:-$DEFAULT_HOST}
PORT=${PORT:-$DEFAULT_PORT}
GRPC_PORT=${GRPC_PORT:-$DEFAULT_GRPC_PORT}
LOG_LEVEL=${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}
DEBUG=${DEBUG:-false}

# 检查服务状态
check_service_status() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  端口 $port 已被占用 ($service_name)"
        read -p "是否要停止现有服务并重启？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pkill -f "$service_name" || true
            sleep 2
        else
            echo "❌ 取消启动"
            exit 1
        fi
    fi
}

# 启动C++后端服务
start_cpp_backend() {
    echo "🔧 启动C++后端服务..."
    
    # 检查可执行文件
    if [ ! -f "./build/ai_assistant_server" ]; then
        echo "❌ C++服务未找到，请先运行构建脚本"
        echo "   运行: ./scripts/build.sh"
        exit 1
    fi
    
    # 检查端口
    check_service_status $GRPC_PORT "ai_assistant_server"
    
    # 启动服务
    echo "📡 在端口 $GRPC_PORT 启动gRPC服务..."
    nohup ./build/ai_assistant_server \
        --port=$GRPC_PORT \
        --log-level=$LOG_LEVEL \
        > logs/grpc_server.log 2>&1 &
    
    GRPC_PID=$!
    echo "✅ gRPC服务已启动 (PID: $GRPC_PID)"
    
    # 等待服务启动
    sleep 3
    
    # 验证服务
    if ! kill -0 $GRPC_PID 2>/dev/null; then
        echo "❌ gRPC服务启动失败，请查看日志: logs/grpc_server.log"
        exit 1
    fi
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
    echo "📁 创建必要目录..."
    mkdir -p logs
    mkdir -p data
    mkdir -p python/plugins
    echo "✅ 目录创建完成"
}

# 健康检查
health_check() {
    echo "🏥 执行健康检查..."
    
    # 检查gRPC服务
    if ! nc -z localhost $GRPC_PORT 2>/dev/null; then
        echo "❌ gRPC服务健康检查失败"
        return 1
    fi
    
    # 检查API服务
    if ! curl -s http://localhost:$PORT/health >/dev/null; then
        echo "❌ API服务健康检查失败"
        return 1
    fi
    
    echo "✅ 所有服务健康检查通过"
    return 0
}

# 显示服务信息
show_service_info() {
    echo ""
    echo "🎉 AI Assistant 服务启动成功！"
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

# 主函数
main() {
    echo "AI Assistant 服务启动脚本 v1.0.0"
    echo "======================================"
    
    # 解析参数
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
            --debug)
                DEBUG=true
                shift
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --host HOST         API服务主机 (默认: $DEFAULT_HOST)"
                echo "  --port PORT         API服务端口 (默认: $DEFAULT_PORT)"
                echo "  --grpc-port PORT    gRPC服务端口 (默认: $DEFAULT_GRPC_PORT)"
                echo "  --debug             启用调试模式"
                echo "  --log-level LEVEL   日志级别 (默认: $DEFAULT_LOG_LEVEL)"
                echo "  --help              显示帮助"
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                echo "使用 --help 查看帮助"
                exit 1
                ;;
        esac
    done
    
    # 设置信号处理
    trap cleanup SIGINT SIGTERM
    
    # 执行启动步骤
    setup_directories
    start_cpp_backend
    start_python_api
    
    # 等待服务完全启动
    sleep 5
    
    # 健康检查
    if health_check; then
        show_service_info
        
        if [ "$DEBUG" = "false" ]; then
            echo "按 Ctrl+C 停止服务"
            wait
        fi
    else
        echo "❌ 服务启动失败，请检查日志"
        cleanup
        exit 1
    fi
}

# 执行主函数
main "$@"