"""
统一模型管理API
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from core.adapters import (
    AdapterManager, OpenAIAdapter, GeminiAdapter, ClaudeAdapter,
    LlamaCppAdapter, OllamaAdapter, ModelInfo, ProviderType
)


logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型配置"""
    id: str
    name: str
    provider: str
    engine: str  # local|cloud
    enabled: bool = True
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_path: Optional[str] = None
    gpu_layers: int = 0
    context_length: int = 4096
    max_tokens: int = 2048
    temperature: float = 0.7
    config: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EngineStatus:
    """引擎状态"""
    name: str
    status: str  # running|stopped|error
    provider: str
    models_loaded: List[str]
    memory_usage_mb: Optional[float] = None
    gpu_utilization: Optional[float] = None
    active_sessions: int = 0
    last_check: Optional[str] = None
    error: Optional[str] = None


class UnifiedModelManager:
    """统一模型管理器"""
    
    def __init__(self, grpc_client=None):
        self.adapter_manager = AdapterManager()
        self.grpc_client = grpc_client
        self.model_configs: Dict[str, ModelConfig] = {}
        self.initialized = False
        
        # 默认配置
        self.default_configs = {
            "openai": {
                "endpoint": "https://api.openai.com/v1",
                "default_model": "gpt-3.5-turbo",
                "timeout": 60
            },
            "gemini": {
                "default_model": "gemini-1.5-pro",
                "generation_config": {
                    "top_p": 0.8,
                    "top_k": 40
                }
            },
            "claude": {
                "endpoint": "https://api.anthropic.com",
                "default_model": "claude-3-sonnet-20240229",
                "version": "2023-06-01"
            },
            "llamacpp": {
                "model_path": "./models",
                "default_model": "qwen3:4b",
                "gpu_layers": 35,
                "threads": 8,
                "context_length": 4096
            },
            "ollama": {
                "endpoint": "http://localhost:11434",
                "default_model": "qwen2.5:4b",
                "timeout": 60
            }
        }
    
    async def initialize(self, config: Dict[str, Any] = None) -> bool:
        """初始化模型管理器"""
        try:
            logger.info("初始化统一模型管理器...")
            
            # 加载配置
            if config:
                await self.load_configuration(config)
            else:
                await self._load_default_configuration()
            
            # 初始化适配器
            init_results = await self.adapter_manager.initialize_all()
            
            # 检查初始化结果
            success_count = sum(1 for success in init_results.values() if success)
            total_count = len(init_results)
            
            logger.info(f"适配器初始化完成: {success_count}/{total_count} 成功")
            
            self.initialized = True
            return success_count > 0
            
        except Exception as e:
            logger.error(f"模型管理器初始化失败: {e}")
            return False
    
    async def load_configuration(self, config: Dict[str, Any]):
        """加载配置"""
        engines_config = config.get("engines", {})
        
        # 配置OpenAI适配器
        if "openai" in engines_config and engines_config["openai"].get("enabled", False):
            openai_config = {**self.default_configs["openai"], **engines_config["openai"]}
            adapter = OpenAIAdapter(openai_config)
            self.adapter_manager.register_adapter("openai", adapter)
        
        # 配置Gemini适配器
        if "gemini" in engines_config and engines_config["gemini"].get("enabled", False):
            gemini_config = {**self.default_configs["gemini"], **engines_config["gemini"]}
            adapter = GeminiAdapter(gemini_config)
            self.adapter_manager.register_adapter("gemini", adapter)
        
        # 配置Claude适配器
        if "claude" in engines_config and engines_config["claude"].get("enabled", False):
            claude_config = {**self.default_configs["claude"], **engines_config["claude"]}
            adapter = ClaudeAdapter(claude_config)
            self.adapter_manager.register_adapter("claude", adapter)
        
        # 配置llama.cpp适配器
        if "llamacpp" in engines_config and engines_config["llamacpp"].get("enabled", False):
            llamacpp_config = {**self.default_configs["llamacpp"], **engines_config["llamacpp"]}
            llamacpp_config["grpc_client"] = self.grpc_client
            adapter = LlamaCppAdapter(llamacpp_config)
            self.adapter_manager.register_adapter("llamacpp", adapter)
        
        # 配置Ollama适配器
        if "ollama" in engines_config and engines_config["ollama"].get("enabled", False):
            ollama_config = {**self.default_configs["ollama"], **engines_config["ollama"]}
            adapter = OllamaAdapter(ollama_config)
            self.adapter_manager.register_adapter("ollama", adapter)
    
    async def _load_default_configuration(self):
        """加载默认配置"""
        import os
        
        # 检查环境变量并创建默认适配器
        if os.getenv("OPENAI_API_KEY"):
            config = self.default_configs["openai"].copy()
            config["api_key"] = os.getenv("OPENAI_API_KEY")
            adapter = OpenAIAdapter(config)
            self.adapter_manager.register_adapter("openai", adapter)
        
        if os.getenv("GEMINI_API_KEY"):
            config = self.default_configs["gemini"].copy()
            config["api_key"] = os.getenv("GEMINI_API_KEY")
            adapter = GeminiAdapter(config)
            self.adapter_manager.register_adapter("gemini", adapter)
        
        if os.getenv("CLAUDE_API_KEY"):
            config = self.default_configs["claude"].copy()
            config["api_key"] = os.getenv("CLAUDE_API_KEY")
            adapter = ClaudeAdapter(config)
            self.adapter_manager.register_adapter("claude", adapter)
        
        # 本地模型适配器（如果gRPC客户端可用）
        if self.grpc_client:
            config = self.default_configs["llamacpp"].copy()
            config["grpc_client"] = self.grpc_client
            adapter = LlamaCppAdapter(config)
            self.adapter_manager.register_adapter("llamacpp", adapter)
        
        # Ollama适配器（检查是否可用）
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        adapter = OllamaAdapter(self.default_configs["ollama"])
                        self.adapter_manager.register_adapter("ollama", adapter)
        except:
            pass  # Ollama不可用
    
    async def get_available_models(self) -> List[ModelInfo]:
        """获取所有可用模型"""
        all_models = []
        
        for adapter_name, adapter in self.adapter_manager.adapters.items():
            try:
                if adapter.is_healthy():
                    models = await adapter.get_available_models()
                    all_models.extend(models)
            except Exception as e:
                logger.error(f"获取 {adapter_name} 模型列表失败: {e}")
        
        return all_models
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """获取指定模型信息"""
        models = await self.get_available_models()
        for model in models:
            if model.id == model_id:
                return model
        return None
    
    async def check_model_health(self, model_id: str) -> Dict[str, Any]:
        """检查模型健康状态"""
        adapter = self.adapter_manager.get_adapter_by_model(model_id)
        if not adapter:
            # 尝试从所有适配器查找
            models = await self.get_available_models()
            for model in models:
                if model.id == model_id:
                    adapter = self.adapter_manager.get_adapter_by_provider(model.provider)
                    break
        
        if adapter:
            return await adapter.health_check()
        else:
            return {
                "status": "not_found",
                "error": f"模型 {model_id} 未找到"
            }
    
    async def get_engines_status(self) -> Dict[str, EngineStatus]:
        """获取所有引擎状态"""
        status_dict = {}
        
        health_results = await self.adapter_manager.health_check_all()
        
        for adapter_name, health_data in health_results.items():
            adapter = self.adapter_manager.get_adapter(adapter_name)
            
            if adapter:
                models = []
                try:
                    model_infos = await adapter.get_available_models()
                    models = [model.id for model in model_infos]
                except:
                    pass
                
                status_dict[adapter_name] = EngineStatus(
                    name=adapter_name,
                    status=health_data.get("status", "unknown"),
                    provider=adapter.provider_type.value if adapter.provider_type else "unknown",
                    models_loaded=models,
                    memory_usage_mb=health_data.get("memory_usage_mb"),
                    gpu_utilization=health_data.get("gpu_utilization"),
                    active_sessions=health_data.get("active_sessions", 0),
                    last_check=health_data.get("last_check"),
                    error=health_data.get("error")
                )
        
        return status_dict
    
    async def add_model(self, model_config: ModelConfig) -> bool:
        """添加新模型配置"""
        try:
            self.model_configs[model_config.id] = model_config
            
            # 如果是新的适配器类型，创建并注册适配器
            provider = model_config.provider
            
            if provider not in self.adapter_manager.adapters:
                adapter = await self._create_adapter(model_config)
                if adapter:
                    self.adapter_manager.register_adapter(provider, adapter)
                    success = await adapter.initialize()
                    return success
            
            return True
            
        except Exception as e:
            logger.error(f"添加模型配置失败: {e}")
            return False
    
    async def remove_model(self, model_id: str) -> bool:
        """移除模型配置"""
        try:
            if model_id in self.model_configs:
                del self.model_configs[model_id]
                return True
            return False
        except Exception as e:
            logger.error(f"移除模型配置失败: {e}")
            return False
    
    async def update_model_config(self, model_id: str, updates: Dict[str, Any]) -> bool:
        """更新模型配置"""
        try:
            if model_id in self.model_configs:
                for key, value in updates.items():
                    if hasattr(self.model_configs[model_id], key):
                        setattr(self.model_configs[model_id], key, value)
                return True
            return False
        except Exception as e:
            logger.error(f"更新模型配置失败: {e}")
            return False
    
    async def _create_adapter(self, model_config: ModelConfig):
        """根据配置创建适配器"""
        provider = model_config.provider
        config = model_config.config or {}
        
        if model_config.api_key:
            config["api_key"] = model_config.api_key
        if model_config.endpoint:
            config["endpoint"] = model_config.endpoint
        
        if provider == "openai":
            return OpenAIAdapter(config)
        elif provider == "gemini":
            return GeminiAdapter(config)
        elif provider == "claude":
            return ClaudeAdapter(config)
        elif provider == "llamacpp":
            config["grpc_client"] = self.grpc_client
            config["model_path"] = model_config.model_path
            config["gpu_layers"] = model_config.gpu_layers
            config["context_length"] = model_config.context_length
            return LlamaCppAdapter(config)
        elif provider == "ollama":
            return OllamaAdapter(config)
        
        return None
    
    def get_adapter_manager(self) -> AdapterManager:
        """获取适配器管理器"""
        return self.adapter_manager
    
    async def cleanup(self):
        """清理资源"""
        await self.adapter_manager.cleanup_all()
        logger.info("模型管理器资源已清理")