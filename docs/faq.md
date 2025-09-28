# 常见问题解答 (FAQ)

## 安装和部署

### Q1: 如何快速开始使用AI Assistant？

**A:** 按照以下步骤快速开始：

1. **克隆项目**：
   ```bash
   git clone https://github.com/your-org/ai-assistant.git
   cd ai-assistant
   ```

2. **环境准备**：
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **构建项目**：
   ```bash
   ./scripts/build.sh
   ```

4. **配置环境**：
   ```bash
   cp .env.example .env
   # 编辑.env文件，添加必要的API密钥
   ```

5. **启动服务**：
   ```bash
   ./scripts/run_server.sh
   ```

6. **测试CLI**：
   ```bash
   python start_cli.py
   ```

### Q2: 支持哪些操作系统？

**A:** AI Assistant支持以下操作系统：

- **Linux**: Ubuntu 20.04+, CentOS 8+, Debian 10+
- **macOS**: 10.15+ (Catalina及以上)
- **Windows**: 10/11 (需要WSL2或原生支持)

推荐使用Linux系统以获得最佳性能。

### Q3: 最低系统要求是什么？

**A:** 

| 组件 | 最低要求 | 推荐配置 |
|------|---------|----------|
| CPU | 2核心 | 4核心+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 20GB | 50GB+ |
| 网络 | 稳定互联网连接 | 10Mbps+ |

### Q4: 如何更新到最新版本？

**A:** 

1. **备份数据**：
   ```bash
   cp ai_assistant.db ai_assistant.db.backup
   cp -r config config.backup
   ```

2. **更新代码**：
   ```bash
   git pull origin main
   ```

3. **更新依赖**：
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **重新构建**：
   ```bash
   ./scripts/build.sh --clean
   ```

5. **重启服务**：
   ```bash
   ./scripts/run_server.sh
   ```

## 配置和使用

### Q5: 如何配置API密钥？

**A:** 

1. **编辑配置文件**：
   ```bash
   cp .env.example .env
   vim .env
   ```

2. **添加必要的密钥**：
   ```bash
   # Google Gemini API密钥
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # OpenAI API密钥（可选）
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **验证配置**：
   ```bash
   python -c "from python.core.config import settings; print('API keys configured')"
   ```

### Q6: 支持哪些AI模型？

**A:** 

**本地模型**：
- qwen2.5:4b (默认)
- llama2:7b
- codellama:7b
- mistral:7b

**云端模型**：
- Google Gemini Pro
- OpenAI GPT-3.5/GPT-4
- Anthropic Claude (计划支持)

**切换模型**：
```bash
# 通过环境变量
export OLLAMA_DEFAULT_MODEL=llama2:7b

# 通过CLI命令
[session] > /config set model llama2:7b
```

### Q7: 如何创建自定义插件？

**A:** 

1. **创建插件目录**：
   ```bash
   mkdir python/plugins/my_plugin
   cd python/plugins/my_plugin
   ```

2. **创建插件文件**：
   ```python
   # main.py
   from python.sdk.plugin_base import PluginBase
   
   class MyPlugin(PluginBase):
       async def execute(self, context):
           return {"result": "Hello from my plugin!"}
   ```

3. **创建配置文件**：
   ```json
   # plugin.json
   {
       "name": "my_plugin",
       "version": "1.0.0",
       "description": "My custom plugin",
       "entry_point": "main:MyPlugin",
       "dependencies": []
   }
   ```

4. **启用插件**：
   ```bash
   [session] > /plugins enable my_plugin
   ```

详细信息请参考[插件开发指南](plugins.md)。

### Q8: 如何备份和恢复会话数据？

**A:** 

**备份**：
```bash
# 备份数据库
sqlite3 ai_assistant.db ".backup backup_$(date +%Y%m%d).db"

# 导出特定会话
[session] > /session export my_conversation.json
```

**恢复**：
```bash
# 恢复数据库
sqlite3 ai_assistant.db ".restore backup_20231201.db"

# 导入会话
[session] > /session import my_conversation.json
```

## 性能和优化

### Q9: 如何提高响应速度？

**A:** 

1. **使用本地模型**：
   ```bash
   # 配置优先使用本地模型
   export LOCAL_MODEL_PRIORITY=high
   ```

2. **启用缓存**：
   ```bash
   # 在.env中配置
   REDIS_URL=redis://localhost:6379
   CACHE_ENABLED=true
   ```

3. **优化系统资源**：
   ```bash
   # 增加工作进程数
   export WORKERS=8
   
   # 优化内存使用
   export MEMORY_CACHE_SIZE=2048
   ```

4. **使用SSD存储**和充足的内存。

### Q10: 系统占用内存过高怎么办？

**A:** 

1. **查看内存使用**：
   ```bash
   # 检查进程内存
   ps aux | grep ai-assistant
   
   # 系统内存状态
   free -h
   ```

2. **优化配置**：
   ```bash
   # 减少缓存大小
   export MEMORY_CACHE_SIZE=512
   
   # 减少工作进程
   export WORKERS=2
   
   # 限制历史记录
   export HISTORY_SIZE=100
   ```

3. **启用内存监控**：
   ```bash
   # 监控内存使用
   python -m memory_profiler python/main.py
   ```

### Q11: 如何优化Docker容器性能？

**A:** 

1. **资源限制**：
   ```bash
   docker run -d \
     --memory=4g \
     --cpus=2 \
     --name ai-assistant \
     ai-assistant:latest
   ```

2. **存储优化**：
   ```bash
   # 使用本地存储卷
   -v /fast/ssd/path:/app/data
   
   # 或使用tmpfs（临时数据）
   --tmpfs /app/tmp:rw,noexec,nosuid,size=1g
   ```

3. **网络优化**：
   ```bash
   # 使用host网络（适用于单机）
   --network host
   ```

## 故障排除

### Q12: 服务启动失败，显示端口被占用

**A:** 

1. **查找占用进程**：
   ```bash
   lsof -i :8000
   lsof -i :50051
   ```

2. **解决方案**：
   ```bash
   # 方案1：杀死占用进程
   sudo kill -9 <PID>
   
   # 方案2：更改端口
   export PORT=8080
   export GRPC_PORT=50052
   
   # 方案3：使用启动脚本的强制选项
   ./scripts/run_server.sh --force
   ```

### Q13: API调用返回"Connection refused"错误

**A:** 

1. **检查服务状态**：
   ```bash
   # 检查进程是否运行
   ps aux | grep ai-assistant
   
   # 检查端口是否开放
   netstat -tlnp | grep 8000
   ```

2. **检查配置**：
   ```bash
   # 验证配置文件
   cat .env | grep -E "HOST|PORT"
   
   # 测试本地连接
   curl http://localhost:8000/health
   ```

3. **查看日志**：
   ```bash
   tail -f logs/api_server.log
   tail -f logs/grpc_server.log
   ```

### Q14: AI响应质量不佳或不相关

**A:** 

1. **检查模型配置**：
   ```bash
   [session] > /status
   # 查看当前使用的模型
   ```

2. **优化提示词**：
   - 使用更具体、清晰的问题
   - 提供必要的上下文信息
   - 尝试分解复杂问题

3. **切换模型**：
   ```bash
   # 尝试使用云端模型
   [session] > /config set cloud_model_priority high
   
   # 或切换本地模型
   [session] > /config set local_model qwen2.5:7b
   ```

4. **清理会话上下文**：
   ```bash
   [session] > /session new
   ```

### Q15: 插件加载失败

**A:** 

1. **检查插件状态**：
   ```bash
   [session] > /plugins list
   [session] > /plugins info plugin_name
   ```

2. **常见问题排查**：
   ```bash
   # 检查插件文件
   ls -la python/plugins/plugin_name/
   
   # 验证配置格式
   python -m json.tool python/plugins/plugin_name/plugin.json
   
   # 检查依赖
   pip list | grep plugin_dependency
   ```

3. **手动测试插件**：
   ```python
   # 在Python控制台中测试
   from python.plugins.plugin_name.main import PluginClass
   plugin = PluginClass()
   result = plugin.execute({})
   ```

### Q16: Docker容器无法启动

**A:** 

1. **检查Docker状态**：
   ```bash
   docker --version
   docker info
   systemctl status docker
   ```

2. **查看容器日志**：
   ```bash
   docker logs ai-assistant
   docker inspect ai-assistant
   ```

3. **常见解决方案**：
   ```bash
   # 清理旧容器
   docker rm -f ai-assistant
   
   # 重新拉取镜像
   docker pull ghcr.io/your-org/ai-assistant:latest
   
   # 检查权限
   sudo usermod -aG docker $USER
   newgrp docker
   ```

## 开发和定制

### Q17: 如何为项目贡献代码？

**A:** 

1. **准备开发环境**：
   ```bash
   git clone https://github.com/your-org/ai-assistant.git
   cd ai-assistant
   git checkout -b feature/my-feature
   ```

2. **安装开发依赖**：
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **代码质量检查**：
   ```bash
   # 格式化代码
   black python/ ui/
   isort python/ ui/
   
   # 类型检查
   mypy python/
   
   # 运行测试
   pytest tests/
   ```

4. **提交规范**：
   参考[贡献指南](../CONTRIBUTING.md)

### Q18: 如何添加新的AI模型支持？

**A:** 

1. **扩展模型引擎**：
   ```python
   # 在 python/core/ 中添加新的客户端
   class NewModelClient:
       async def chat(self, messages):
           # 实现模型调用逻辑
           pass
   ```

2. **更新配置**：
   ```python
   # 在 config.py 中添加配置项
   NEW_MODEL_API_KEY: Optional[str] = None
   NEW_MODEL_ENDPOINT: str = "https://api.newmodel.com"
   ```

3. **集成到调度器**：
   ```python
   # 在 orchestrator.py 中添加路由逻辑
   if model_type == "new_model":
       return await self.new_model_client.chat(messages)
   ```

### Q19: 如何自定义Web界面？

**A:** 

1. **进入Web目录**：
   ```bash
   cd ui/web/ai-assistant-gui
   ```

2. **安装依赖**：
   ```bash
   npm install
   ```

3. **开发模式**：
   ```bash
   npm run dev
   ```

4. **自定义组件**：
   ```typescript
   // 在 src/components/ 中创建新组件
   export const MyComponent = () => {
       return <div>My Custom Component</div>;
   };
   ```

5. **构建生产版本**：
   ```bash
   npm run build
   ```

## 安全和隐私

### Q20: 如何确保数据安全？

**A:** 

1. **加密配置**：
   ```bash
   # 使用环境变量而非文件存储密钥
   export GEMINI_API_KEY=your_key
   
   # 限制文件权限
   chmod 600 .env
   ```

2. **网络安全**：
   ```bash
   # 使用HTTPS
   # 配置防火墙
   ufw allow 22
   ufw allow 443
   ufw deny 8000  # 不直接暴露API端口
   ```

3. **数据隔离**：
   - 为不同用户/项目创建独立实例
   - 定期备份和清理数据
   - 使用数据库加密

### Q21: 会话数据是否会被发送到云端？

**A:** 

**本地模式**：
- 使用本地模型时，对话数据不会离开本机
- 可通过配置禁用云端模型：`CLOUD_MODEL_ENABLED=false`

**云端模式**：
- 使用Gemini/OpenAI等服务时，数据会发送到相应的API服务
- 可查看各服务商的隐私政策
- 建议对敏感信息使用本地模式

**配置建议**：
```bash
# 仅使用本地模型
export CLOUD_MODEL_ENABLED=false
export LOCAL_MODEL_PRIORITY=high

# 或为敏感对话创建独立会话
[session] > /session new --local-only
```

## 社区和支持

### Q22: 在哪里可以获得帮助？

**A:** 

1. **文档资源**：
   - [官方文档](docs/)
   - [API参考](docs/api.md)
   - [故障排除指南](docs/troubleshooting.md)

2. **社区支持**：
   - [GitHub Issues](https://github.com/your-org/ai-assistant/issues)
   - [GitHub Discussions](https://github.com/your-org/ai-assistant/discussions)
   - [Discord社区](https://discord.gg/ai-assistant)

3. **报告问题**：
   - 提供详细的错误信息
   - 包含系统环境信息
   - 附上相关日志文件

### Q23: 如何参与社区建设？

**A:** 

1. **代码贡献**：
   - 修复Bug
   - 添加新功能
   - 改进文档

2. **社区活动**：
   - 回答其他用户的问题
   - 分享使用经验
   - 创建教程和示例

3. **反馈建议**：
   - 提出功能需求
   - 报告问题和Bug
   - 参与设计讨论

---

如果您的问题没有在此FAQ中找到答案，请：

1. 查看[完整文档](docs/)
2. 搜索[已有Issues](https://github.com/your-org/ai-assistant/issues)
3. 在[Discussions](https://github.com/your-org/ai-assistant/discussions)中提问
4. 创建新的[Issue](https://github.com/your-org/ai-assistant/issues/new)

我们会持续更新这个FAQ，感谢您的使用和反馈！