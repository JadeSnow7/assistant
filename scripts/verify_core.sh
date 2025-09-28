#!/bin/bash

# AI Assistant 快速验证脚本
set -e

echo "🤖 AI Assistant 核心逻辑验证"
echo "======================================"

# 检查Python环境
echo "🐍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2)
echo "✅ Python版本: $python_version"

# 检查必要的Python包
echo "📦 检查Python依赖..."
required_packages=("fastapi" "uvicorn" "pydantic" "aiohttp" "aiosqlite")
missing_packages=()

for package in "${required_packages[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        missing_packages+=("$package")
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo "❌ 缺少依赖包: ${missing_packages[*]}"
    echo "请运行: pip3 install ${missing_packages[*]}"
    exit 1
fi

echo "✅ 所有必需依赖已安装"

# 创建必要的目录
echo "📁 创建项目目录..."
mkdir -p logs data src/plugins

# 运行核心逻辑测试
echo "🧪 运行核心逻辑测试..."
python3 test_core.py

test_result=$?

if [ $test_result -eq 0 ]; then
    echo ""
    echo "🎉 核心逻辑验证完成！"
    echo "✅ 所有组件运行正常"
    echo ""
    echo "📝 下一步:"
    echo "   1. 启动服务: python3 src/main.py"
    echo "   2. 测试API: ./cli_client.py chat \"你好\""
    echo "   3. 查看文档: docs/architecture.md"
else
    echo ""
    echo "⚠️  核心逻辑验证发现问题"
    echo "请查看上面的错误信息并解决"
    echo ""
    echo "🔧 常见解决方案:"
    echo "   1. 安装缺失依赖: pip3 install -r requirements.txt"
    echo "   2. 检查Python版本: python3 --version (需要3.8+)"
    echo "   3. 查看详细日志: 检查上面的输出"
fi

exit $test_result