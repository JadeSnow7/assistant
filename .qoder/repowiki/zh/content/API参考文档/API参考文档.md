
# API参考文档

<cite>
**本文档中引用的文件**
- [api_router.py](file://python/agent/api_router.py)
- [schemas.py](file://python/models/schemas.py)
- [orchestrator.py](file://python/agent/orchestrator.py)
- [cli_client.py](file://cli_client.py)
</cite>

## 目录
1. [简介](#简介)
2. [/chat接口](#chat接口)
3. [/chat/stream接口](#chatchatstream接口)
4. [/tasks接口](#tasks接口)
5. [/plugins接口](#plugins接口)
6. [/system/status接口](#systemstatus接口)
7. [/memory/query接口](#memoryquery接口)
8. [错误处理模式](#错误处理模式)
9. [速率限制策略](#速率限制策略)
10. [API版本控制方案](#api版本控制方案)

## 简介
nex项目提供了一套完整的RESTful API，用于与AI助手进行交互。所有API端点均通过FastAPI框架实现，并遵循统一的认证和错误处理机制。API基础路径为`/api/v1`，支持JSON格式的请求和响应。

```mermaid
graph TD
Client[客户端] --> |HTTP请求| Chat[/chat]
Client --> |SSE流式| ChatStream[/chat/stream]
Client --> |后台任务| Tasks[/tasks]
Client --> |插件管理| Plugins[/plugins]
Client --> |系统监控| Status[/system/status]
Client --> |记忆查询| Memory[/memory/query]
Chat --> Orchestrator[AgentOrchestrator]
ChatStream --> Orchestrator
Tasks --> Orchestrator
Plugins --> Orchestrator
Status --> Orchestrator
Memory --> Orchestrator
Orchestrator --> GRPC[gRPC客户端]
Orchestrator --> Cloud[云服务客户端]
Orchestrator --> PluginManager[插件管理器]
Orchestrator --> MemoryManager[记忆管理器]
```

**Diagram sources**
- [api_router.py](file://python/agent/api_router.py)
- [orchestrator.py](file://python/agent/orchestrator.py)

**Section sources**
- [api_router.py](file://python/agent/api_router.py)
- [main.py](file://python/main.py)

## /chat接口
主要的AI对话入口，接收用户消息并返回结构化响应。

### 接口详情
- **HTTP方法**: POST
- **URL路径**: `/api/v1/chat`
- **认证要求**: 需要有效的API密钥（通过`Authorization`头传递）

### 请求参数
使用`ChatRequest`模型定义请求体：

```json
{
  "message": "用户输入的消息内容",
  "session_id": "会话ID（可选）",
  "max_tokens": 1024,
  "temperature": 0.7,
  "model_type": "auto_select",
  "preferred_model": "gpt-4",
  "stream": false,
  "context": {}
}
```

**字段说明:**
- `message`: 用户消息（必需）
- `session_id`: 会话标识符，用于保持上下文
- `max_tokens`: 响应的最大token数
- `temperature`: 温度参数，控制输出的随机性
- `model_type`: 模型类型选择（local_small, cloud_large, plugin, auto_select）
- `preferred_model`: 首选模型名称
- `stream`: 是否启用流式响应
- `context`: 额外的上下文信息

### 响应格式
返回`ChatResponse`模型：

```json
{
  "content": "AI回复内容",
  "session_id": "会话ID",
  "model_used": "实际使用的模型类型",
  "reasoning": "模型选择原因",
  "token_count": 150,
  "latency_ms": 1200,
  "confidence": 0.95,
  "timestamp": "2024-01-01T12:00:00Z",
  "error": null
}
```

### 状态码
- `200`: 成功处理请求
- `500`: 服务器内部错误

### 认证要求
需要在请求头中包含有效的API密钥：
```
Authorization: Bearer <your-api-key>
```

### 典型使用场景
适用于需要完整响应的常规对话场景，如问答、内容生成等。

**Section sources**
- [api_router.py](file://python/agent/api_router.py#L30-L45)
- [schemas.py](file://python/models/schemas.py#L25-L55)

## /chat/stream接口
实时流式响应接口，通过Server-Sent Events (SSE)协议传输数据。

### 接口详情
- **HTTP方法**: POST
- **URL路径**: `/api/v1/chat/stream`
- **认证要求**: 需要有效的API密钥

### 请求参数
与`/chat`接口相同，使用`ChatRequest`模型。

### 流式响应协议
采用SSE（Server-Sent Events）协议，响应格式如下：
```
data: {"content": "部分", "session_id": "sess_123"}
data: {"content": "响应内容", "session_id": "sess_123"}
data: {"content": "完成", "session_id": "sess_123"}
```

每个数据块以`data:`开头，后跟JSON格式的数据，以`\n\n`结束。客户端需要逐行解析这些事件。

### 响应头部
- `Content-Type: text/plain`
- `Cache-Control: no-cache`
- `Transfer-Encoding: chunked`

### 状态码
- `200`: 成功建立流式连接
- `500`: 流式处理失败

### WebSocket连接机制
虽然此接口使用HTTP流而非WebSocket，但系统也支持WebSocket连接，路径为`/ws`，用于更复杂的双向通信场景。

### curl命令示例
```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"message": "写一首关于春天的诗"}'
```

### Python客户端调用
```python
import aiohttp
import asyncio

async def stream_chat():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/v1/chat/stream",
            json={"message": "你好"},
            headers={"Authorization": "Bearer your-api-key"}
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(data['content'], end='', flush=True)
```

### 背后的orchestrator逻辑路径
1. 调用`AgentOrchestrator.process_chat_stream()`方法
2. 分析用户意图
3. 决策执行策略（本地模型、云端模型或插件）
4. 生成异步生成器，逐块返回响应
5. 处理异常情况，发送错误信息

### 典型使用场景
适用于需要实时反馈的长文本生成场景，如写作辅助、代码生成等。

**Section sources**
- [api_router.py](file://python/agent/api_router.py#L48-L75)
- [orchestrator.py](file://python/agent/orchestrator.py#L85-L142)
- [cli_client.py](file://cli_client.py#L75-L96)

## /tasks接口
后台任务管理接口，支持创建和查询任务状态。

### 创建任务
#### 接口详情
- **HTTP方法**: POST
- **URL路径**: `/api/v1/tasks`
- **认证要求**: 需要有效的API密钥

#### 请求参数
使用`TaskRequest`模型：

```json
{
  "task_type": "任务类型",
  "description": "任务描述",
  "parameters": {},
  "priority": 1,
  "timeout_seconds": 300
}
```

#### 响应格式
返回`TaskResponse`模型：

```json
{
  "task_id": "任务唯一标识",
  "status": "created",
  "progress": null,
  "result": null,
  "error": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "message": "任务已创建"
}
```

### 查询任务状态
#### 接口详情
- **HTTP方法**: GET
- **URL路径**: `/api/v1/tasks/{task_id}`
- **认证要求**: 需要有效的API密钥

#### 响应状态码
- `200`: 成功获取任务状态
- `404`: 任务不存在
- `500`: 服务器内部错误

### 背后的orchestrator逻辑路径
1. 调用`AgentOrchestrator.create_background_task()`创建任务
2. 将任务加入异步队列
3. 启动后台任务处理器协程
4. 通过`get_task_status()`查询任务执行进度

### 典型使用场景
适用于耗时较长的操作，如批量数据处理、复杂计算等。

**Section sources**
- [api_router.py](file://python/agent/api_router.py#L78-L120)
- [schemas.py](file://python/models/schemas.py#L65-L85)

## /plugins接口
插件管理系统接口，用于管理和查询可用插件。

### 获取插件列表
#### 接口详情
- **HTTP方法**: GET
- **URL路径**: `/api/v1/plugins`
- **认证要求**: 需要有效的API密钥

#### 响应格式
返回`PluginInfo`模型数组：

```json
[
  {
    "name": "weather_plugin",
    "version": "1.0.0",
    "description": "天气查询插件",
    "author": "AI Assistant Team",
    "capabilities": ["weather_query"],
    "enabled": true,
    "config_schema": {},
    "dependencies": ["requests"]
  }
]
```

### 启用/禁用插件
#### 接口详情
- **HTTP方法**: POST
- **URL路径**: 
  - `/api/v1/plugins/{plugin_name}/enable`
  - `/api/v1/plugins/{plugin_name}/disable`
- **认证要求**: 需要有效的API密钥

#### 响应格式
```json
{
  "message": "插件 weather_plugin 已启用"
}
```

### 背后的orchestrator逻辑路径
1. 调用`PluginManager.get_available_plugins()`获取插件列表
2. 通过`enable_plugin()`和`disable_plugin()`方法管理插件状态
3. 插件配置基于`plugin.json`文件定义

### 典型使用场景
用于动态扩展系统功能，如添加新的数据源、集成第三方服务等。

**Section sources**
- [api_router.py](file://python/agent/api_router.py#L123-L162)
- [schemas.py](file://python/models/schemas.py#L95-L115)

## /system/status接口
系统状态监控接口，提供全面的系统健康检查。

### 接口详情
- **HTTP方法**: GET
- **URL路径**: `/api/v1/system/status`
- **认证要求**: 需要有效的API密钥

### 响应格式
返回`SystemStatus`模型：

```json
{
  "cpu_usage": 25.5,
  "memory_usage": 45.2,
  "gpu_usage": 15.0,
  "active_sessions": 10,
  "