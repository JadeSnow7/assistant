#!/bin/bash

# AI Assistant 现代化UI测试脚本

echo "🚀 启动AI Assistant现代化UI测试"
echo "=================================="

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠️  未找到Python虚拟环境，正在创建..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装Python依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

# 启动后端服务（后台运行）
echo "🔧 启动后端服务..."
python src/main.py &
BACKEND_PID=$!

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 5

# 测试后端健康状态
echo "🔍 检查后端服务状态..."
curl -s http://localhost:8000/health || echo "⚠️  后端服务可能未正常启动"

echo ""
echo "✅ 现代化UI系统已启动！"
echo ""
echo "可用的界面："
echo "  🖥️  Web GUI:  http://localhost:5173"
echo "  💻 CLI模式:  python modern_cli.py"
echo ""
echo "测试命令："
echo "  python modern_cli.py --help"
echo "  python modern_cli.py --url http://localhost:8000"
echo ""
echo "按任意键停止所有服务..."
read -n 1

# 清理进程
echo "🧹 清理服务..."
kill $BACKEND_PID 2>/dev/null
pkill -f "python.*main.py" 2>/dev/null
pkill -f "npm.*run.*dev" 2>/dev/null

echo "👋 测试完成！"