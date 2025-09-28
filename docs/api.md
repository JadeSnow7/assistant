# API 接口文档

## 概述

AI Assistant 提供 RESTful API 和 WebSocket 接口，支持多种客户端接入。

## 基础信息

- **基础URL**: `http://localhost:8000`
- **API版本**: `v1`
- **内容类型**: `application/json`
- **编码**: `UTF-8`

## 认证

当前版本使用可选的API密钥认证：

```http
Authorization: Bearer your_api_key_here
```

## 接口列表

### 1. 健康检查

检查服务状态和各组件健康状况。

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-27T16:30:00Z",
  "components": {
    "grpc_client": "healthy",
    "orchestrator": "healthy",
    "cloud_client": "healthy",
    "ollama_client": "healthy"
  }
}
```

### 2. 聊天对话

发送消息并获取AI响应。

```http
POST /api/v1/chat
```

**请求参数**:
```json
{
  "message": "你好，请介绍一下你自己",
  "session_id": "user-session-001",
  "max_tokens": 1024,
  "temperature": 0.7,
  "preferred_model": "auto"
}
```

**参数说明**:
- `message` (必填): 用户消息内容
- `session_id` (可选): 会话ID，用于上下文记忆
- `max_tokens` (可选): 最大token数，默认1024
- `temperature` (可选): 生成温度，0.0-1.0，默认0.7
- `preferred_model` (可选): 首选模型，auto/local/cloud

**响应示例**:
```json
{
  "content": "你好！我是AI Assistant，一个基于混合架构的智能助手...",
  "session_id": "user-session-001",
  "model_used": "local_small",
  "reasoning": "简单任务，本地模型处理",
  "token_count": 45,
  "latency_ms": 1234.5,
  "confidence": 0.92,
  "timestamp": "2025-09-27T16:30:00Z",
  "error": null
}
```

### 3. 流式聊天

实时流式获取AI响应。

```http
POST /api/v1/chat/stream
```

**请求参数**: 同聊天接口

**响应**: Server-Sent Events (SSE) 流

```
data: {"content": "你好", "finished": false}
data: {"content": "！我是", "finished": false}
data: {"content": "AI Assistant", "finished": false}
data: {"content": "", "finished": true, "total_tokens": 45}
```

### 4. 系统状态

获取详细的系统运行状态。

```http
GET /api/v1/system/status
```

**响应示例**:
```json
{
  "status": "running",
  "uptime": 86400,
  "cpu_usage": 25.5,
  "memory_usage": 68.2,
  "gpu_usage": 15.3,
  "active_sessions": 12,
  "total_requests": 1527,
  "avg_response_time": 1856.3,
  "model_stats": {
    "local_requests": 1200,
    "cloud_requests": 327,
    "success_rate": 98.5
  }
}
```

### 5. 插件管理

#### 5.1 获取插件列表

```http
GET /api/v1/plugins
```

**响应示例**:
```json
[
  {
    "name": "weather",
    "version": "1.0.0",
    "description": "天气查询插件",
    "enabled": true,
    "capabilities": ["weather_query", "forecast"],
    "author": "AI Assistant Team"
  }
]
```

#### 5.2 执行插件

```http
POST /api/v1/plugins/{plugin_name}/execute
```

**请求参数**:
```json
{
  "command": "get_weather",
  "parameters": {
    "city": "北京",
    "days": 3
  }
}
```

### 6. 记忆管理

#### 6.1 获取会话记忆

```http
GET /api/v1/memory/{session_id}
```

**响应示例**:
```json
{
  "session_id": "user-session-001",
  "created_at": "2025-09-27T15:00:00Z",
  "updated_at": "2025-09-27T16:30:00Z",
  "message_count": 15,
  "context": {
    "user_preferences": {
      "language": "zh-CN",
      "response_style": "friendly"
    },
    "recent_topics": ["AI技术", "编程", "项目架构"]
  }
}
```

#### 6.2 清除会话记忆

```http
DELETE /api/v1/memory/{session_id}
```

## WebSocket 接口

### 连接地址
```
ws://localhost:8000/ws/{session_id}
```

### 消息格式

**发送消息**:
```json
{
  "type": "chat",
  "message": "你好",
  "timestamp": "2025-09-27T16:30:00Z"
}
```

**接收消息**:
```json
{
  "type": "response",
  "content": "你好！",
  "model_used": "local_small",
  "timestamp": "2025-09-27T16:30:01Z"
}
```

## 错误处理

### HTTP状态码

- `200` - 成功
- `400` - 请求参数错误
- `401` - 认证失败
- `429` - 请求频率限制
- `500` - 服务器内部错误
- `503` - 服务不可用

### 错误响应格式

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "请求参数不正确",
    "details": {
      "field": "message",
      "reason": "消息内容不能为空"
    }
  },
  "timestamp": "2025-09-27T16:30:00Z"
}
```

## 限制说明

- **请求频率**: 每用户每分钟最多60次请求
- **消息长度**: 单次消息最大10,000字符
- **并发连接**: 每IP最多100个WebSocket连接
- **文件上传**: 最大10MB

## SDK 示例

### Python SDK

```python
import asyncio
import aiohttp

class AIAssistantClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    async def chat(self, message, session_id=None):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/chat",
                json={"message": message, "session_id": session_id}
            ) as response:
                return await response.json()

# 使用示例
async def main():
    client = AIAssistantClient()
    response = await client.chat("你好")
    print(response["content"])

asyncio.run(main())
```

### JavaScript SDK

```javascript
class AIAssistantClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async chat(message, sessionId = null) {
        const response = await fetch(`${this.baseUrl}/api/v1/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        return await response.json();
    }
}

// 使用示例
const client = new AIAssistantClient();
client.chat('你好').then(response => {
    console.log(response.content);
});
```

## 最佳实践

1. **会话管理**: 使用固定的session_id维持对话上下文
2. **错误处理**: 实现重试机制处理网络异常
3. **资源控制**: 根据任务复杂度选择合适的max_tokens
4. **缓存策略**: 对重复请求实现客户端缓存
5. **监控告警**: 监控API响应时间和成功率

## 更新日志

### v1.0.0 (2025-09-27)
- 初始版本发布
- 支持基础聊天功能
- 集成本地和云端模型
- 实现智能路由策略