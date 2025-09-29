"""
统一API接口适配器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProviderType(str, Enum):
    """服务提供商类型"""
    OPENAI = "openai"
    GEMINI = "gemini" 
    CLAUDE = "claude"
    LLAMACPP = "llamacpp"
    OLLAMA = "ollama"
    VLLM = "vllm"


class EngineType(str, Enum):
    """引擎类型"""
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class UnifiedChatRequest:
    """统一聊天请求格式"""
    model: str
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    top_k: Optional[int] = 40
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stream: bool = False
    session_id: Optional[str] = None
    engine: str = "auto"  # auto|local|cloud
    provider: str = "auto"  # auto|openai|gemini|claude|llamacpp|ollama|vllm


@dataclass
class UnifiedChatResponse:
    """统一聊天响应格式"""
    id: str
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    provider: str = ""
    engine: str = ""
    choices: List[Dict[str, Any]] = None
    usage: Optional[Dict[str, int]] = None
    performance: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        if self.choices is None:
            self.choices = []
        if self.created == 0:
            self.created = int(datetime.now().timestamp())


@dataclass
class UnifiedStreamChunk:
    """统一流式响应块"""
    id: str
    object: str = "chat.completion.chunk"
    created: int = 0
    model: str = ""
    provider: str = ""
    choices: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.choices is None:
            self.choices = []
        if self.created == 0:
            self.created = int(datetime.now().timestamp())


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    object: str = "model"
    provider: str = ""
    engine: str = ""
    capabilities: List[str] = None
    context_length: int = 4096
    status: str = "available"  # available|unavailable|loading
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["chat", "completion"]


class BaseAdapter(ABC):
    """统一API适配器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_type = None
        self.engine_type = None
        self.initialized = False
        self.healthy = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化适配器"""
        pass
    
    @abstractmethod
    async def chat_completion(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """聊天完成"""
        pass
    
    @abstractmethod
    async def chat_completion_stream(self, request: UnifiedChatRequest) -> AsyncGenerator[UnifiedStreamChunk, None]:
        """流式聊天完成"""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型列表"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
    
    async def cleanup(self):
        """清理资源"""
        pass
    
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.healthy and self.initialized
    
    def get_provider_type(self) -> ProviderType:
        """获取提供商类型"""
        return self.provider_type
    
    def get_engine_type(self) -> EngineType:
        """获取引擎类型"""
        return self.engine_type
    
    def _generate_response_id(self) -> str:
        """生成响应ID"""
        import uuid
        return f"chatcmpl-{uuid.uuid4().hex[:29]}"
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量（简单方法）"""
        # 简单的token估算，实际应该使用tokenizer
        return max(1, len(text.split()) * 1.3)
    
    def _format_error_response(self, error_msg: str, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """格式化错误响应"""
        return UnifiedChatResponse(
            id=self._generate_response_id(),
            model=request.model,
            provider=self.provider_type.value if self.provider_type else "unknown",
            engine=self.engine_type.value if self.engine_type else "unknown",
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"抱歉，处理请求时发生错误：{error_msg}"
                },
                "finish_reason": "error"
            }],
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )


class AdapterManager:
    """适配器管理器"""
    
    def __init__(self):
        self.adapters: Dict[str, BaseAdapter] = {}
        self.model_to_adapter: Dict[str, str] = {}
        self.provider_to_adapter: Dict[str, str] = {}
    
    def register_adapter(self, name: str, adapter: BaseAdapter):
        """注册适配器"""
        self.adapters[name] = adapter
        if adapter.provider_type:
            self.provider_to_adapter[adapter.provider_type.value] = name
    
    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        """获取适配器"""
        return self.adapters.get(name)
    
    def get_adapter_by_provider(self, provider: str) -> Optional[BaseAdapter]:
        """根据提供商获取适配器"""
        adapter_name = self.provider_to_adapter.get(provider)
        if adapter_name:
            return self.adapters.get(adapter_name)
        return None
    
    def get_adapter_by_model(self, model: str) -> Optional[BaseAdapter]:
        """根据模型获取适配器"""
        adapter_name = self.model_to_adapter.get(model)
        if adapter_name:
            return self.adapters.get(adapter_name)
        return None
    
    async def initialize_all(self) -> Dict[str, bool]:
        """初始化所有适配器"""
        results = {}
        for name, adapter in self.adapters.items():
            try:
                results[name] = await adapter.initialize()
            except Exception as e:
                results[name] = False
                print(f"初始化适配器 {name} 失败: {e}")
        return results
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """检查所有适配器健康状态"""
        results = {}
        for name, adapter in self.adapters.items():
            try:
                if adapter.is_healthy():
                    results[name] = await adapter.health_check()
                else:
                    results[name] = {"status": "unhealthy", "error": "adapter not initialized"}
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return results
    
    async def cleanup_all(self):
        """清理所有适配器"""
        for adapter in self.adapters.values():
            try:
                await adapter.cleanup()
            except Exception as e:
                print(f"清理适配器失败: {e}")
    
    def list_available_models(self) -> List[ModelInfo]:
        """列出所有可用模型"""
        models = []
        for adapter in self.adapters.values():
            if adapter.is_healthy():
                try:
                    # 这里应该是异步调用，但为了简化先同步处理
                    # 实际使用时需要改为异步
                    pass
                except Exception as e:
                    print(f"获取模型列表失败: {e}")
        return models