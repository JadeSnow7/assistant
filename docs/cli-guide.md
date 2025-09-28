# CLI使用指南

## 概述

AI Assistant提供了两种CLI界面：
1. **简化CLI** (`start_cli.py`) - 快速体验和测试
2. **现代化CLI** (`ui/cli/modern_cli.py`) - 完整功能和企业级体验

## 快速开始

### 启动简化CLI

```bash
# 激活虚拟环境（如果使用）
source venv/bin/activate

# 启动简化CLI
python start_cli.py
```

### 启动现代化CLI

```bash
# 方式1：直接启动
python ui/cli/modern_cli.py

# 方式2：带参数启动
python ui/cli/modern_cli.py --url http://localhost:8000 --debug
```

## CLI界面对比

| 功能特性 | 简化CLI | 现代化CLI |
|---------|---------|----------|
| 基础对话 | ✅ | ✅ |
| 命令系统 | ❌ | ✅ |
| 会话管理 | 基础 | 完整 |
| 界面美化 | 基础 | Rich/Textual |
| 流式显示 | ❌ | ✅ |
| 插件支持 | ❌ | ✅ |
| 调试功能 | ❌ | ✅ |

## 现代化CLI详细功能

### 1. 基础对话

```bash
# 启动后直接输入消息
[session-abc123] > 你好，我是新用户

# AI会智能回复
🤖 AI: 你好！欢迎使用AI Assistant。我可以帮你解答问题、处理任务和提供各种服务。有什么我可以帮助你的吗？
```

### 2. 命令系统

#### 系统命令
```bash
# 查看帮助
[session-abc123] > /help

# 查看系统状态
[session-abc123] > /status

# 健康检查
[session-abc123] > /health

# 查看会话信息
[session-abc123] > /session

# 退出程序
[session-abc123] > /exit
```

#### 配置命令
```bash
# 查看当前配置
[session-abc123] > /config show

# 设置配置项
[session-abc123] > /config set debug true

# 重置配置
[session-abc123] > /config reset
```

#### 插件命令
```bash
# 列出可用插件
[session-abc123] > /plugins list

# 启用插件
[session-abc123] > /plugins enable weather

# 禁用插件
[session-abc123] > /plugins disable weather

# 插件信息
[session-abc123] > /plugins info weather
```

### 3. 会话管理

#### 创建和切换会话
```bash
# 创建新会话
[session-abc123] > /session new

# 列出所有会话
[session-abc123] > /session list

# 切换会话
[session-abc123] > /session switch def456

# 删除会话
[session-abc123] > /session delete old789
```

#### 会话导出和导入
```bash
# 导出当前会话
[session-abc123] > /session export conversation.json

# 导入会话
[session-abc123] > /session import conversation.json
```

### 4. 高级功能

#### 流式响应
现代化CLI支持实时流式响应显示：

```bash
[session-abc123] > 请写一篇关于AI发展的文章

🤖 AI: 正在思考...

# 文字会逐步显示，如同真人打字
人工智能的发展历程...
[实时显示内容]
```

#### 多行输入
```bash
# 使用反斜杠继续输入
[session-abc123] > 这是第一行 \
> 这是第二行 \
> 这是第三行

# 或使用三重引号
[session-abc123] > """
> 这是多行输入
> 可以包含代码
> 和格式化文本
> """
```

#### 历史记录
```bash
# 查看命令历史
[session-abc123] > /history

# 重复上一个命令
[session-abc123] > !!

# 重复指定历史命令
[session-abc123] > !5
```

## 配置文件

### CLI配置文件位置

```bash
# 系统配置
~/.config/ai-assistant/cli.json

# 项目配置
./ui/cli/config.py
```

### 配置选项

```json
{
  "api_url": "http://localhost:8000",
  "timeout": 30,
  "max_retries": 3,
  "debug": false,
  "theme": "dark",
  "auto_save": true,
  "history_size": 1000,
  "plugins": {
    "enabled": ["weather", "calculator"],
    "auto_load": true
  },
  "display": {
    "show_timestamps": true,
    "show_model_info": true,
    "streaming": true,
    "colors": true
  }
}
```

## 主题定制

### 内置主题

```bash
# 切换到暗色主题
[session-abc123] > /theme dark

# 切换到亮色主题  
[session-abc123] > /theme light

# 切换到经典主题
[session-abc123] > /theme classic
```

### 自定义主题

创建自定义主题文件 `~/.config/ai-assistant/themes/mytheme.json`:

```json
{
  "name": "mytheme",
  "colors": {
    "primary": "#00ff00",
    "secondary": "#0066cc", 
    "success": "#28a745",
    "warning": "#ffc107",
    "error": "#dc3545",
    "background": "#1a1a1a",
    "text": "#ffffff"
  },
  "styles": {
    "user_message": "bold cyan",
    "ai_response": "green",
    "system_message": "yellow",
    "error_message": "bold red"
  }
}
```

## 插件使用

### 天气插件示例

```bash
# 启用天气插件
[session-abc123] > /plugins enable weather

# 查询天气
[session-abc123] > 北京的天气怎么样？

🤖 AI: 🌤️ 北京当前天气：
温度：22°C
湿度：65%
风速：3.2 m/s
天气：多云
```

### 计算器插件示例

```bash
# 启用计算器插件
[session-abc123] > /plugins enable calculator

# 进行计算
[session-abc123] > 计算 123 * 456 + 789

🤖 AI: 📊 计算结果：
123 × 456 + 789 = 56,877
```

## 快捷键

### 基础快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+C` | 中断当前操作 |
| `Ctrl+D` | 退出程序 |
| `Ctrl+L` | 清屏 |
| `↑/↓` | 浏览历史命令 |
| `Tab` | 命令补全 |
| `Ctrl+R` | 反向搜索历史 |

### 高级快捷键

| 快捷键 | 功能 |
|--------|------|
| `Alt+Enter` | 多行输入模式 |
| `Ctrl+U` | 清除当前行 |
| `Ctrl+W` | 删除上一个单词 |
| `Ctrl+A` | 光标移到行首 |
| `Ctrl+E` | 光标移到行尾 |

## 故障排除

### 常见问题

#### 1. 连接失败
```bash
❌ 连接错误: Connection refused

解决方案：
1. 确认后端服务已启动
2. 检查端口配置是否正确
3. 验证网络连接
```

#### 2. 命令不识别
```bash
❌ 未知命令: /unknown

解决方案：
1. 使用 /help 查看可用命令
2. 检查命令拼写
3. 确认插件是否已启用
```

#### 3. 插件加载失败
```bash
❌ 插件加载失败: weather

解决方案：
1. 检查插件文件是否存在
2. 验证插件配置
3. 查看错误日志
```

### 调试模式

启用调试模式获取详细信息：

```bash
# 启动时启用调试
python ui/cli/modern_cli.py --debug

# 运行时启用调试
[session-abc123] > /config set debug true
```

调试模式下会显示：
- 详细的错误信息
- API请求/响应
- 插件执行过程
- 性能统计信息

### 日志文件

CLI日志文件位置：
```bash
# 应用日志
./logs/cli.log

# 错误日志  
./logs/cli_error.log

# 调试日志
./logs/cli_debug.log
```

## 性能优化

### 提升响应速度

```bash
# 启用本地缓存
[session-abc123] > /config set cache.enabled true

# 调整超时时间
[session-abc123] > /config set timeout 60

# 启用请求压缩
[session-abc123] > /config set compression true
```

### 减少内存使用

```bash
# 限制历史记录大小
[session-abc123] > /config set history_size 500

# 禁用不必要的插件
[session-abc123] > /plugins disable unused_plugin

# 定期清理会话
[session-abc123] > /session cleanup
```

## 最佳实践

### 1. 会话管理
- 为不同任务创建不同会话
- 定期导出重要对话
- 清理无用的历史会话

### 2. 插件使用
- 只启用需要的插件
- 定期更新插件版本
- 查看插件文档了解功能

### 3. 配置优化
- 根据网络情况调整超时
- 选择合适的主题提升体验
- 启用自动保存防止数据丢失

### 4. 安全建议
- 不要在CLI中输入敏感信息
- 定期清理历史记录
- 使用安全的API连接

---

通过本指南，您应该能够熟练使用AI Assistant的CLI界面。如有其他问题，请参考[FAQ文档](faq.md)或提交Issue。