"""
数据模型和Schema定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ModelType(str, Enum):
    """模型类型枚举"""
    LOCAL_SMALL = "local_small"
    CLOUD_LARGE = "cloud_large"
    PLUGIN = "plugin"
    AUTO_SELECT = "auto_select"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============ 聊天相关模型 ============

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    max_tokens: Optional[int] = Field(1024, description="最大token数")
    temperature: Optional[float] = Field(0.7, description="温度参数")
    model_type: Optional[ModelType] = Field(ModelType.AUTO_SELECT, description="指定模型类型")
    preferred_model: Optional[str] = Field(None, description="首选模型名称")
    stream: bool = Field(False, description="是否流式响应")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str = Field(..., description="回复内容")
    session_id: Optional[str] = Field(None, description="会话ID")
    model_used: ModelType = Field(..., description="实际使用的模型类型")
    reasoning: Optional[str] = Field(None, description="选择该模型的原因")
    token_count: Optional[int] = Field(None, description="使用的token数量")
    latency_ms: Optional[float] = Field(None, description="响应延迟(毫秒)")
    confidence: Optional[float] = Field(None, description="置信度")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    error: Optional[str] = Field(None, description="错误信息")


# ============ 任务相关模型 ============

class TaskRequest(BaseModel):
    """任务请求模型"""
    task_type: str = Field(..., description="任务类型")
    description: str = Field(..., description="任务描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="任务参数")
    priority: int = Field(1, description="任务优先级(1-10)")
    timeout_seconds: Optional[int] = Field(None, description="超时时间(秒)")


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: Optional[float] = Field(None, description="进度百分比")
    result: Optional[Any] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    message: Optional[str] = Field(None, description="状态消息")


# ============ 插件相关模型 ============

class PluginInfo(BaseModel):
    """插件信息模型"""
    name: str = Field(..., description="插件名称")
    version: str = Field(..., description="插件版本")
    description: str = Field(..., description="插件描述")
    author: str = Field(..., description="插件作者")
    capabilities: List[str] = Field(..., description="插件能力列表")
    enabled: bool = Field(..., description="是否启用")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="配置结构")
    dependencies: Optional[List[str]] = Field(None, description="依赖列表")


class PluginExecuteRequest(BaseModel):
    """插件执行请求模型"""
    plugin_name: str = Field(..., description="插件名称")
    command: str = Field(..., description="执行命令")
    parameters: Optional[Dict[str, Any]] = Field(None, description="命令参数")
    session_id: Optional[str] = Field(None, description="会话ID")


class PluginExecuteResponse(BaseModel):
    """插件执行响应模型"""
    plugin_name: str = Field(..., description="插件名称")
    command: str = Field(..., description="执行的命令")
    result: Any = Field(..., description="执行结果")
    success: bool = Field(..., description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: Optional[float] = Field(None, description="执行时间(毫秒)")


# ============ 系统相关模型 ============

class SystemInfo(BaseModel):
    """系统信息模型"""
    cpu_usage: float = Field(..., description="CPU使用率(%)")
    memory_usage: float = Field(..., description="内存使用率(%)")
    memory_total_gb: float = Field(..., description="总内存(GB)")
    memory_free_gb: float = Field(..., description="可用内存(GB)")
    disk_usage: float = Field(..., description="磁盘使用率(%)")
    disk_free_gb: float = Field(..., description="可用磁盘空间(GB)")
    gpu_usage: float = Field(..., description="GPU使用率(%)")
    gpu_memory_usage: float = Field(..., description="GPU内存使用率(%)")
    cpu_cores: int = Field(..., description="CPU核心数")
    os_info: str = Field(..., description="操作系统信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class SystemStatus(BaseModel):
    """系统状态模型"""
    cpu_usage: float = Field(..., description="CPU使用率")
    memory_usage: float = Field(..., description="内存使用率")
    gpu_usage: float = Field(..., description="GPU使用率")
    active_sessions: int = Field(..., description="活跃会话数")
    total_requests: int = Field(..., description="总请求数")
    avg_response_time: float = Field(..., description="平均响应时间(毫秒)")
    components_health: Dict[str, bool] = Field(..., description="组件健康状态")
    uptime_seconds: int = Field(..., description="运行时间(秒)")


# ============ 记忆相关模型 ============

class MemoryEntry(BaseModel):
    """记忆条目模型"""
    id: str = Field(..., description="记忆ID")
    session_id: str = Field(..., description="会话ID")
    content: str = Field(..., description="记忆内容")
    content_type: str = Field(..., description="内容类型")
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    importance: float = Field(0.5, description="重要性评分")


class MemoryQuery(BaseModel):
    """记忆查询模型"""
    query_text: str = Field(..., description="查询文本")
    session_id: Optional[str] = Field(None, description="限制会话ID")
    limit: int = Field(10, description="返回结果数量限制")
    similarity_threshold: float = Field(0.7, description="相似度阈值")


class MemoryResponse(BaseModel):
    """记忆查询响应模型"""
    results: List[MemoryEntry] = Field(..., description="查询结果")
    total_count: int = Field(..., description="总数量")


# ============ 配置相关模型 ============

class ModelConfig(BaseModel):
    """模型配置"""
    name: str = Field(..., description="模型名称")
    type: ModelType = Field(..., description="模型类型")
    endpoint: Optional[str] = Field(None, description="API端点")
    api_key: Optional[str] = Field(None, description="API密钥")
    max_tokens: int = Field(2048, description="最大token数")
    temperature: float = Field(0.7, description="默认温度")
    enabled: bool = Field(True, description="是否启用")


class AppConfig(BaseModel):
    """应用配置"""
    app_name: str = Field("AI Assistant", description="应用名称")
    version: str = Field("1.0.0", description="版本号")
    debug: bool = Field(False, description="调试模式")
    host: str = Field("0.0.0.0", description="主机地址")
    port: int = Field(8000, description="端口号")
    allowed_origins: List[str] = Field(["*"], description="允许的来源")
    grpc_server_address: str = Field("localhost:50051", description="gRPC服务地址")
    database_url: str = Field("sqlite:///./ai_assistant.db", description="数据库URL")
    redis_url: str = Field("redis://localhost:6379", description="Redis URL")
    log_level: str = Field("INFO", description="日志级别")


# ============ WebSocket相关模型 ============

class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(..., description="消息类型")
    data: Any = Field(..., description="消息数据")
    session_id: Optional[str] = Field(None, description="会话ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ConnectionInfo(BaseModel):
    """连接信息模型"""
    connection_id: str = Field(..., description="连接ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    connected_at: datetime = Field(default_factory=datetime.now, description="连接时间")
    last_activity: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    user_agent: Optional[str] = Field(None, description="用户代理")
    ip_address: Optional[str] = Field(None, description="IP地址")