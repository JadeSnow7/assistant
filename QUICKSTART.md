# 快速入门指南

## 🎯 5分钟快速体验

### 第一步：环境准备

```bash
# 检查 Python 版本 (需要 3.10+)
python3 --version

# 检查 Git
git --version
```

### 第二步：项目安装

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/ai-assistant.git
cd ai-assistant

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

### 第三步：配置API密钥

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置（使用你喜欢的编辑器）
nano .env
```

**最小配置**:
```env
# 必填：Google Gemini API Key
GEMINI_API_KEY=your_actual_api_key_here

# 其他配置保持默认即可
DEBUG=true
HOST=127.0.0.1
PORT=8000
```

> 💡 **获取 Gemini API Key**: 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)

### 第四步：启动服务

```bash
# 启动 AI Assistant 服务
python src/main.py
```

看到类似输出表示启动成功：
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 第五步：测试对话

**方法一：使用 CLI 客户端**
```bash
# 新开一个终端窗口
cd ai-assistant
source venv/bin/activate
python cli_client.py
```

**方法二：使用 curl 命令**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下你自己", "session_id": "quickstart-test"}'
```

**方法三：使用浏览器访问API文档**
打开 http://localhost:8000/docs

## 🧪 体验核心功能

### 1. 智能路由测试

**简单任务（本地处理）**:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "simple-test"}'
```

**复杂任务（云端处理）**:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "请详细分析人工智能在医疗领域的应用前景，包括机遇与挑战", "session_id": "complex-test"}'
```

### 2. 会话记忆测试

```bash
# 第一轮对话
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "我叫张三，今年25岁", "session_id": "memory-test"}'

# 第二轮对话（测试记忆）
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你还记得我的名字吗？", "session_id": "memory-test"}'
```

### 3. 系统状态检查

```bash
# 健康检查
curl http://localhost:8000/health

# 系统状态
curl http://localhost:8000/api/v1/system/status
```

## 🔧 进阶配置

### 1. 本地模型设置（可选）

如果你想使用本地模型，需要安装 Ollama：

```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 拉取模型
ollama pull qwen3:4b

# 验证模型
ollama list
```

更新 `.env` 配置：
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=qwen3:4b
```

### 2. 数据库配置

**开发环境（默认SQLite）**:
```env
DATABASE_URL=sqlite:///./ai_assistant.db
```

**生产环境（PostgreSQL）**:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/ai_assistant
```

### 3. 日志配置

```env
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_FILE=./logs/app.log      # 日志文件路径
```

## 🚀 CLI 客户端使用

### 启动 CLI 客户端

```bash
python cli_client.py
```

### CLI 命令

```bash
# 基础对话
> 你好，请介绍一下你的功能

# 查看帮助
> /help

# 查看系统状态
> /status

# 清除会话记忆
> /clear

# 切换会话
> /session new-session-id

# 退出客户端
> /quit
```

### CLI 高级功能

```bash
# 指定模型
> /model local
> 用本地模型回答：什么是机器学习？

> /model cloud  
> 用云端模型回答：详细解释深度学习原理

# 调整参数
> /temperature 0.9
> /max_tokens 2048
```

## 📱 Web API 使用

### 基础聊天接口

```javascript
// JavaScript 示例
const response = await fetch('http://localhost:8000/api/v1/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: '你好，世界！',
    session_id: 'web-session-001',
    max_tokens: 1024,
    temperature: 0.7
  })
});

const data = await response.json();
console.log(data.content);
```

### 流式响应

```javascript
// 流式聊天示例
const response = await fetch('http://localhost:8000/api/v1/chat/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: '请写一首关于春天的诗',
    session_id: 'stream-session'
  })
});

const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = new TextDecoder().decode(value);
  console.log(chunk);
}
```

## 🔍 故障排查

### 常见问题

**1. 端口被占用**
```bash
# 检查端口使用情况
lsof -i :8000

# 杀死占用进程
kill -9 <PID>

# 或者修改端口
export PORT=8001
```

**2. 依赖安装失败**
```bash
# 更新 pip
pip install --upgrade pip

# 清理缓存重新安装
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

**3. API 密钥错误**
```bash
# 检查环境变量
echo $GEMINI_API_KEY

# 重新设置
export GEMINI_API_KEY=your_actual_key
```

**4. 模型响应慢**
```bash
# 检查网络连接
curl -I https://generativelanguage.googleapis.com

# 查看日志
tail -f logs/app.log
```

### 调试模式

开启详细日志：
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

查看详细错误信息：
```bash
python python/main.py --debug
```

## 📋 下一步学习

### 核心文档
- [📋 API 接口文档](docs/api.md) - 详细的API参考
- [🔌 插件开发指南](docs/plugins.md) - 学习如何开发插件
- [🚀 部署指南](docs/deployment.md) - 生产环境部署
- [👨‍💻 开发者指南](docs/DEVELOPER_GUIDE.md) - 深入技术细节

### 示例项目
- 开发天气查询插件
- 集成自定义模型
- 构建 Web 界面
- 实现多模态功能

### 社区参与
- [🤝 贡献指南](CONTRIBUTING.md)
- [📝 问题反馈](https://github.com/your-repo/ai-assistant/issues)
- [💬 讨论区](https://github.com/your-repo/ai-assistant/discussions)

## 🎉 恭喜！

你已经成功搭建了 AI Assistant 开发环境，可以开始探索更多功能了！

如果遇到问题，请查看：
- [故障排查文档](docs/troubleshooting.md)
- [常见问题 FAQ](docs/faq.md)
- [GitHub Issues](https://github.com/your-repo/ai-assistant/issues)

---

**快乐编程！** 🚀