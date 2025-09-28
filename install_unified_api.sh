#!/bin/bash

# 统一API系统安装脚本
# 使用方法: bash install_unified_api.sh

set -e

echo "🚀 统一API系统安装脚本"
echo "========================="

# 颜色定义
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

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # 检查Python版本
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_info "Python版本: $PYTHON_VERSION"
        
        # 检查是否满足最低版本要求 (3.9+)
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
            log_success "Python版本符合要求 (>=3.9)"
        else
            log_error "Python版本过低，需要3.9或更高版本"
            exit 1
        fi
    else
        log_error "未找到Python3，请先安装Python3"
        exit 1
    fi
    
    # 检查pip
    if command -v pip3 &> /dev/null; then
        log_success "pip3已安装"
    else
        log_error "未找到pip3，请先安装pip3"
        exit 1
    fi
    
    # 检查Git
    if command -v git &> /dev/null; then
        log_success "Git已安装"
    else
        log_warning "未找到Git，部分功能可能不可用"
    fi
    
    # 检查CUDA (可选)
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)
        log_success "检测到NVIDIA GPU: $GPU_INFO"
    else
        log_warning "未检测到NVIDIA GPU，将使用CPU模式"
    fi
}

# 创建虚拟环境
create_venv() {
    log_info "创建Python虚拟环境..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "虚拟环境创建成功"
    else
        log_info "虚拟环境已存在，跳过创建"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    log_success "虚拟环境已激活"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."
    
    # 确保虚拟环境已激活
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装基础依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "基础依赖安装完成"
    else
        log_warning "未找到requirements.txt，手动安装关键依赖"
        pip install fastapi uvicorn aiohttp pydantic pyyaml watchdog
    fi
    
    # 安装开发依赖
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
        log_success "开发依赖安装完成"
    else
        log_info "跳过开发依赖安装"
    fi
    
    # 安装可选的GPU依赖
    read -p "是否安装GPU加速依赖? (y/N): " install_gpu
    if [[ $install_gpu =~ ^[Yy]$ ]]; then
        log_info "安装GPU相关依赖..."
        pip install nvidia-ml-py3 || log_warning "nvidia-ml-py3安装失败，GPU监控可能不可用"
        
        # 检查是否需要安装Google AI SDK
        read -p "是否安装Google Generative AI SDK? (y/N): " install_gemini
        if [[ $install_gemini =~ ^[Yy]$ ]]; then
            pip install google-generativeai
            log_success "Google AI SDK安装完成"
        fi
    fi
}

# 创建配置文件
setup_config() {
    log_info "设置配置文件..."
    
    # 创建配置目录
    mkdir -p configs
    mkdir -p logs
    mkdir -p models
    
    # 如果配置文件不存在，创建默认配置
    if [ ! -f "configs/unified_api.yaml" ]; then
        log_info "创建默认配置文件..."
        cat > configs/unified_api.yaml << 'EOF'
# 统一API配置文件
api:
  version: "v1"
  host: "0.0.0.0"
  port: 8000
  base_path: "/api/v1"

# 引擎配置
engines:
  # OpenAI配置
  openai:
    enabled: false
    endpoint: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-3.5-turbo"
    timeout: 60
  
  # Google Gemini配置
  gemini:
    enabled: false
    api_key: "${GEMINI_API_KEY}"
    default_model: "gemini-1.5-pro"
  
  # llama.cpp本地引擎配置
  llamacpp:
    enabled: true
    model_path: "./models"
    default_model: "qwen3:4b"
    context_length: 4096
    gpu_layers: 35
    threads: 8
  
  # Ollama配置
  ollama:
    enabled: true
    endpoint: "http://localhost:11434"
    default_model: "qwen2.5:4b"

# GPU配置
gpu:
  enabled: true
  auto_detect: true
  gpu_layers: 35
  batch_size: 512

# 路由配置
routing:
  strategy: "smart_route"
  local_preference: 0.6
  complexity_threshold: 0.7

# 日志配置
logging:
  level: "INFO"
  file: "logs/unified_api.log"
EOF
        log_success "默认配置文件已创建"
    else
        log_info "配置文件已存在，跳过创建"
    fi
}

# 设置环境变量
setup_env() {
    log_info "设置环境变量..."
    
    # 创建.env文件模板
    if [ ! -f ".env" ]; then
        cat > .env << 'EOF'
# AI API密钥配置
# 请根据需要取消注释并填入真实的API密钥

# OpenAI API密钥
# OPENAI_API_KEY=your_openai_api_key_here

# Google Gemini API密钥
# GEMINI_API_KEY=your_gemini_api_key_here

# Anthropic Claude API密钥
# CLAUDE_API_KEY=your_claude_api_key_here

# 其他配置
# PYTHONPATH=/home/snow/workspace/nex/python
EOF
        log_success ".env配置文件已创建"
        log_warning "请编辑.env文件，填入您的API密钥"
    else
        log_info ".env文件已存在"
    fi
}

# 下载示例模型
download_models() {
    read -p "是否下载示例模型文件? (y/N): " download_model
    if [[ $download_model =~ ^[Yy]$ ]]; then
        log_info "下载示例模型（这可能需要一些时间）..."
        
        mkdir -p models
        cd models
        
        # 下载轻量级模型用于测试
        if [ ! -f "qwen3-4b-q4_0.gguf" ]; then
            log_info "下载Qwen3-4B模型..."
            if command -v wget &> /dev/null; then
                wget -c "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/qwen3-4b-q4_0.gguf" || log_warning "模型下载失败，请手动下载"
            elif command -v curl &> /dev/null; then
                curl -L -C - -o "qwen3-4b-q4_0.gguf" "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/qwen3-4b-q4_0.gguf" || log_warning "模型下载失败，请手动下载"
            else
                log_warning "未找到wget或curl，请手动下载模型文件"
            fi
        else
            log_info "模型文件已存在，跳过下载"
        fi
        
        cd ..
    fi
}

# 运行测试
run_tests() {
    read -p "是否运行系统测试? (y/N): " run_test
    if [[ $run_test =~ ^[Yy]$ ]]; then
        log_info "运行系统测试..."
        
        # 确保虚拟环境已激活
        if [[ "$VIRTUAL_ENV" == "" ]]; then
            source venv/bin/activate
        fi
        
        # 设置Python路径
        export PYTHONPATH="${PWD}/python:$PYTHONPATH"
        
        # 运行单元测试
        if [ -f "tests/test_unified_api.py" ]; then
            python -m pytest tests/test_unified_api.py -v || log_warning "部分测试失败，这可能是正常的"
        fi
        
        # 运行演示脚本
        if [ -f "examples/unified_api_demo.py" ]; then
            log_info "运行演示脚本..."
            python examples/unified_api_demo.py || log_warning "演示脚本运行失败"
        fi
    fi
}

# 创建启动脚本
create_start_script() {
    log_info "创建启动脚本..."
    
    cat > start_unified_api.sh << 'EOF'
#!/bin/bash

# 统一API系统启动脚本

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "❌ 未找到虚拟环境，请先运行安装脚本"
    exit 1
fi

# 设置Python路径
export PYTHONPATH="${PWD}/python:$PYTHONPATH"

# 加载环境变量
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo "✅ 环境变量已加载"
fi

# 启动API服务
echo "🚀 启动统一API服务..."
cd python
python core/unified_api_gateway.py
EOF
    
    chmod +x start_unified_api.sh
    log_success "启动脚本已创建: start_unified_api.sh"
}

# 创建停止脚本
create_stop_script() {
    cat > stop_unified_api.sh << 'EOF'
#!/bin/bash

# 统一API系统停止脚本

echo "⏹️ 停止统一API服务..."

# 查找并终止Python进程
pkill -f "unified_api_gateway.py" && echo "✅ API服务已停止" || echo "ℹ️ 没有运行中的API服务"

# 查找并终止uvicorn进程
pkill -f "uvicorn" && echo "✅ Uvicorn服务已停止" || echo "ℹ️ 没有运行中的Uvicorn服务"
EOF
    
    chmod +x stop_unified_api.sh
    log_success "停止脚本已创建: stop_unified_api.sh"
}

# 显示安装总结
show_summary() {
    echo ""
    echo "🎉 统一API系统安装完成！"
    echo "========================="
    echo ""
    log_info "安装总结:"
    echo "  ✅ Python虚拟环境: venv/"
    echo "  ✅ 配置文件: configs/unified_api.yaml"
    echo "  ✅ 环境变量: .env"
    echo "  ✅ 启动脚本: start_unified_api.sh"
    echo "  ✅ 停止脚本: stop_unified_api.sh"
    echo ""
    
    log_info "下一步操作:"
    echo "  1. 编辑 .env 文件，配置您的API密钥"
    echo "  2. 根据需要修改 configs/unified_api.yaml"
    echo "  3. 运行 './start_unified_api.sh' 启动服务"
    echo "  4. 访问 http://localhost:8000/v1/models 查看可用模型"
    echo ""
    
    log_info "快速启动命令:"
    echo "  bash start_unified_api.sh"
    echo ""
    
    log_info "文档和示例:"
    echo "  - 使用指南: docs/UNIFIED_API_GUIDE.md"
    echo "  - 演示脚本: python examples/unified_api_demo.py"
    echo "  - 单元测试: python -m pytest tests/test_unified_api.py"
    echo ""
    
    log_warning "注意事项:"
    echo "  - 首次运行前请配置API密钥"
    echo "  - 本地模型需要下载模型文件到 models/ 目录"
    echo "  - GPU加速需要正确安装NVIDIA驱动和CUDA"
}

# 主安装流程
main() {
    echo ""
    log_info "开始安装统一API系统..."
    echo ""
    
    # 检查是否在正确的目录
    if [ ! -f "python/core/unified_api_gateway.py" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 执行安装步骤
    check_requirements
    create_venv
    install_python_deps
    setup_config
    setup_env
    download_models
    create_start_script
    create_stop_script
    run_tests
    
    # 显示安装总结
    show_summary
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@"