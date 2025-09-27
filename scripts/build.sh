#!/bin/bash

# AI Assistant 构建脚本
set -e

echo "🚀 开始构建AI Assistant..."

# 检查依赖
check_dependencies() {
    echo "📋 检查依赖..."
    
    # 检查cmake
    if ! command -v cmake &> /dev/null; then
        echo "❌ CMake未安装，请先安装CMake"
        exit 1
    fi
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3未安装，请先安装Python3"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        echo "❌ pip3未安装，请先安装pip3"
        exit 1
    fi
    
    echo "✅ 依赖检查通过"
}

# 创建构建目录
setup_build_dir() {
    echo "📁 设置构建目录..."
    mkdir -p build
    cd build
}

# 构建C++核心模块
build_cpp() {
    echo "🔨 构建C++核心模块..."
    
    # CMake配置
    cmake .. -DCMAKE_BUILD_TYPE=Release \
             -DCMAKE_INSTALL_PREFIX=../install \
             -DBUILD_TESTS=ON
    
    # 编译
    make -j$(nproc)
    
    # 安装
    make install
    
    echo "✅ C++模块构建完成"
}

# 安装Python依赖
install_python_deps() {
    echo "🐍 安装Python依赖..."
    cd ../python
    
    # 创建虚拟环境(可选)
    if [ "$1" = "--venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        echo "✅ 虚拟环境已创建并激活"
    fi
    
    # 安装依赖
    pip3 install -r ../requirements.txt
    
    echo "✅ Python依赖安装完成"
}

# 运行测试
run_tests() {
    echo "🧪 运行测试..."
    
    # C++测试
    cd ../build
    if [ -f "./tests/test_runner" ]; then
        echo "运行C++测试..."
        ./tests/test_runner
    fi
    
    # Python测试
    cd ../python
    if [ -f "pytest" ] || command -v pytest &> /dev/null; then
        echo "运行Python测试..."
        python -m pytest tests/ -v
    fi
    
    echo "✅ 测试完成"
}

# 主函数
main() {
    echo "AI Assistant 构建脚本 v1.0.0"
    echo "================================"
    
    # 解析参数
    SKIP_TESTS=false
    USE_VENV=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --venv)
                USE_VENV=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --skip-tests    跳过测试"
                echo "  --venv         使用Python虚拟环境"
                echo "  --help         显示帮助"
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                echo "使用 --help 查看帮助"
                exit 1
                ;;
        esac
    done
    
    # 执行构建步骤
    check_dependencies
    setup_build_dir
    build_cpp
    
    if [ "$USE_VENV" = true ]; then
        install_python_deps --venv
    else
        install_python_deps
    fi
    
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi
    
    echo ""
    echo "🎉 构建完成！"
    echo "📝 下一步:"
    echo "   1. 运行服务: ./scripts/run_server.sh"
    echo "   2. 查看文档: docs/README.md"
    echo "   3. 配置插件: 编辑 python/plugins/"
}

# 错误处理
trap 'echo "❌ 构建失败，请查看错误信息"; exit 1' ERR

# 执行主函数
main "$@"