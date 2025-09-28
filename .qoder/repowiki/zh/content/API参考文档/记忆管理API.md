# 记忆管理API

<cite>
**本文档引用的文件**
- [api_router.py](file://python/agent/api_router.py)
- [memory_manager.py](file://python/core/memory_manager.py)
- [schemas.py](file://python/models/schemas.py)
- [config.py](file://python/core/config.py)
</cite>

## 目录
1. [简介](#简介)
2. [/memory/query端点详解](#memoryquery端点详解)
3. 请求参数说明
4. 底层搜索机制
5. 返回结果结构
6. 查询使用示例
7. 隐私与安全措施
8. 性能优化建议

## 简介
本API文档详细说明了系统中`/memory/query`端点的功能和使用方法。该端点允许用户查询其会话上下文记忆，通过语义匹配和条件过滤检索历史对话记录。系统采用基于SQLite的持久化存储，并结合重要性评分机制对结果进行排序。

## /memory/query端点详解

`/memory/query`端点提供了一个强大的接口来检索用户的会话记忆内容。该功能由`AgentOrchestrator`协调，通过`MemoryManager`组件实现具体的搜索逻辑。

```mermaid
sequenceDiagram
participant 客户端 as 客户端应用
participant API路由器 as API路由器
participant 编排器 as AgentOrchestrator
participant 记忆管理器 as MemoryManager
客户端->>API路由器 : POST /memory/query
API路由器->>编排器 : 调用search_memory()
编排器->>记忆管理器 : 执行搜索操作
记忆管理器->>记忆管理器 : 构建SQL查询
记忆管理器->>数据库 : 执行查询并获取结果
数据库-->>记忆管理器 : 返回原始数据
记忆管理器->>记忆管理器 : 转换为MemoryEntry对象
记忆管理器-->>编排器 : 返回结果列表
编排器-->>API路由器 : 响应数据
API路由器-->>客户端 : 返回MemoryResponse
```

**Diagram sources**
- [api_router.py](file://python/agent/api_router.py#L203-L246)
- [memory_manager.py](file://python/core/memory_manager.py#L193-L258)

**Section sources**
- [api_router.py](file://python/agent/api_router.py#L203-L246)
- [memory_manager.py](file://python/core/memory_manager.py#L193-L258)

## 请求参数说明

### 核心参数
| 参数名 | 类型 | 必需 | 默认值 | 描述 |
|-------|------|------|--------|------|
| query_text | 字符串 | 是 | 无 | 要搜索的查询文本，用于匹配用户消息或AI响应 |
| session_id | 字符串 | 否 | null | 限制搜索范围到特定会话ID |
| limit | 整数 | 否 | 10 | 返回结果的最大数量 |
| similarity_threshold | 浮点数 | 否 | 0.7 | 相似度阈值，用于向量搜索 |

这些参数定义在`MemoryQuery`模型中，作为请求体传递给API。

```mermaid
classDiagram
class MemoryQuery {
+string query_text
+Optional~string~ session_id
+int limit
+float similarity_threshold
}
class MemoryResponse {
+MemoryEntry[] results
+int total_count
}
class MemoryEntry {
+string id
+string session_id
+string content
+string content_type
+Optional~float[]~ embedding
+Optional~Dict~str,Any~~ metadata
+datetime created_at
+float importance
}
MemoryQuery --> MemoryResponse : "查询产生"
MemoryResponse --> MemoryEntry : "包含多个"
```

**Diagram sources**
- [schemas.py](file://python/models/schemas.py#L151-L175)
- [schemas.py](file://python/models/schemas.py#L125-L148)

**Section sources**
- [schemas.py](file://python/models/schemas.py#L151-L175)

## 底层搜索机制

当前的记忆搜索机制基于SQL的模糊匹配实现，未来可扩展为基于ChromaDB的向量相似度搜索。

### 搜索流程
```mermaid
flowchart TD
开始([开始搜索]) --> 输入验证["验证输入参数"]
输入验证 --> 条件构建["构建查询条件"]
条件构建 --> SQL生成["生成SQL查询语句"]
SQL生成 --> 数据库执行["执行数据库查询"]
数据库执行 --> 结果处理["处理查询结果"]
结果处理 --> 对象转换["转换为MemoryEntry对象"]
对象转换 --> 排序["按重要性和时间排序"]
排序 --> 返回结果["返回结果列表"]
异常处理["异常处理"] --> 返回空列表["返回空列表"]
条件构建 --> |包含session_id| 添加会话条件["添加session_id条件"]
SQL生成 --> |实际实现| 使用LIKE操作符["使用LIKE进行模糊匹配"]
```

搜索过程首先构建WHERE子句条件：
- 主要条件：`user_message LIKE ? OR ai_response LIKE ?`
- 可选条件：当提供`session_id`时添加`session_id = ?`
- 排序规则：先按`importance_score`降序，再按`timestamp`降序
- 限制数量：使用LIMIT子句限制返回结果

**Section sources**
- [memory_manager.py](file://python/core/memory_manager.py#L193-L226)

## 返回结果结构

### MemoryEntry字段说明
| 字段名 | 类型 | 描述 |
|-------|------|------|
| id | 字符串 | 记忆条目的唯一标识符 |
| session_id | 字符串 | 关联的会话ID |
| content | 字符串 | 组合的对话内容（用户消息和AI响应） |
| content_type | 字符串 | 内容类型，当前为"conversation" |
| embedding | 浮点数数组 | 向量嵌入表示，用于语义搜索 |
| metadata | 键值对 | 附加的元数据信息 |
| created_at | 时间戳 | 记录创建时间 |
| importance | 浮点数 | 重要性评分（0.0-1.0） |

重要性评分通过以下算法计算：
- 基础分：0.5
- 长度加分：总长度超过200字符+0.1，超过500字符再+0.1
- 关键词加分：包含"重要"、"记住"等关键词+0.1
- 问号加分：用户消息包含问号+0.05

```mermaid
flowchart LR
A[开始计算] --> B[基础分0.5]
B --> C{长度>200?}
C --> |是| D[+0.1]
C --> |否| E[不加分]
D --> F{长度>500?}
F --> |是| G[+0.1]
F --> |否| H[结束]
G --> I{包含关键词?}
E --> I
H --> J
I --> |是| J[+0.1]
I --> |否| K[不加分]
J --> L{包含问号?}
L --> |是| M[+0.05]
L --> |否| N[不加分]
M --> O[最终评分]
N --> O
K --> O
```

**Diagram sources**
- [memory_manager.py](file://python/core/memory_manager.py#L350-L366)
- [schemas.py](file://python/models/schemas.py#L125-L148)

**Section sources**
- [memory_manager.py](file://python/core/memory_manager.py#L350-L366)
- [schemas.py](file://python/models/schemas.py#L125-L148)

## 查询使用示例

### 模糊查询示例
```json
{
  "query_text": "AI助手",
  "session_id": "session_123",
  "limit": 5
}
```
此查询将返回session_123会话中所有包含"AI助手"的消息，最多5条记录。

### 全局搜索示例
```json
{
  "query_text": "如何设置",
  "limit": 10
}
```
此查询将在所有会话中搜索包含"如何设置"的内容，返回最相关的10条记录。

### 高相似度搜索
```json
{
  "query_text": "机器学习",
  "similarity_threshold": 0.85,
  "limit": 3
}
```
此查询要求更高的相似度匹配，只返回非常相关的结果。

## 隐私与安全措施

系统实施了多层次的数据保护机制：

```mermaid
graph TB
A[数据收集] --> B[自动脱敏]
B --> C[加密存储]
C --> D[访问控制]
D --> E[审计日志]
E --> F[定期清理]
subgraph 安全措施
B --> B1["移除敏感信息"]
B --> B2["匿名化处理"]
C --> C1["数据库加密"]
D --> D1["API密钥验证"]
D --> D2["用户身份认证"]
E --> E1["记录访问日志"]
F --> F1["基于策略的保留"]
end
```

具体措施包括：
- **访问控制**：通过`get_current_user`依赖注入实现用户身份验证
- **操作审计**：所有查询操作都被记录在日志中
- **数据隔离**：每个用户的记忆数据通过会话ID进行逻辑隔离
- **资源清理**：`cleanup()`方法定期清除内存缓存

**Section sources**
- [api_router.py](file://python/agent/api_router.py#L203-L246)
- [memory_manager.py](file://python/core/memory_manager.py#L363-L366)

## 性能优化建议

为了平衡性能与存储成本，建议采取以下策略：

### 记忆保留周期配置
通过`config.py`中的设置可以调整记忆系统的参数：

```python
# 记忆系统配置
memory_cache_size: int = 1000
memory_similarity_threshold: float = 0.7
```

### 优化策略
| 策略 | 描述 | 影响 |
|------|------|------|
| 限制查询范围 | 使用session_id缩小搜索范围 | 提高查询速度 |
| 合理设置limit | 避免一次性返回过多结果 | 减少网络传输 |
| 适当调整相似度阈值 | 根据场景调整匹配严格度 | 平衡准确率和召回率 |
| 定期清理过期会话 | 删除不再需要的会话记忆 | 节省存储空间 |

建议根据实际使用情况，定期评估和调整这些参数以达到最佳性能。

**Section sources**
- [config.py](file://python/core/config.py#L45-L47)
- [memory_manager.py](file://python/core/memory_manager.py#L29-L35)