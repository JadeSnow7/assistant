"""
Google Gemini适配器
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from .base import (
    BaseAdapter, UnifiedChatRequest, UnifiedChatResponse, 
    UnifiedStreamChunk, ModelInfo, ProviderType, EngineType
)


logger = logging.getLogger(__name__)


class GeminiAdapter(BaseAdapter):
    """Google Gemini适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = ProviderType.GEMINI
        self.engine_type = EngineType.CLOUD
        
        # 配置参数
        self.api_key = config.get("api_key")
        self.default_model = config.get("default_model", "gemini-1.5-pro")
        self.generation_config = config.get("generation_config", {})
        
        # Gemini客户端
        self.client = None
        
        # 支持的模型列表
        self.supported_models = [
            "gemini-1.5-pro",
            "gemini-1.5-flash", 
            "gemini-pro",
            "gemini-pro-vision"
        ]
    
    async def initialize(self) -> bool:
        """初始化Gemini适配器"""
        try:
            if not GEMINI_AVAILABLE:
                logger.error("Gemini SDK不可用，请安装 google-generativeai")
                return False
            
            if not self.api_key:
                logger.error("Gemini API密钥未配置")
                return False
            
            # 配置Gemini客户端
            genai.configure(api_key=self.api_key)
            
            # 测试连接
            health_result = await self.health_check()
            self.healthy = health_result.get("status") == "healthy"
            self.initialized = True
            
            logger.info(f"Gemini适配器初始化{'成功' if self.healthy else '失败'}")
            return self.healthy
            
        except Exception as e:
            logger.error(f"Gemini适配器初始化失败: {e}")
            self.initialized = True
            self.healthy = False
            return False
    
    async def chat_completion(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """Gemini聊天完成"""
        try:
            if not GEMINI_AVAILABLE:
                raise Exception("Gemini SDK不可用")
            
            # 创建模型实例
            model = genai.GenerativeModel(request.model or self.default_model)
            
            # 转换消息格式
            prompt = self._convert_messages_to_prompt(request.messages)
            
            # 生成配置
            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                top_p=request.top_p,
                top_k=request.top_k
            )
            
            # 调用Gemini API
            start_time = datetime.now()
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            )
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # 转换响应格式
            return self._convert_from_gemini_format(response, request, latency_ms)
        
        except Exception as e:
            logger.error(f"Gemini聊天完成失败: {e}")
            return self._format_error_response(str(e), request)
    
    async def chat_completion_stream(self, request: UnifiedChatRequest) -> AsyncGenerator[UnifiedStreamChunk, None]:
        """Gemini流式聊天完成"""
        try:
            if not GEMINI_AVAILABLE:
                raise Exception("Gemini SDK不可用")
            
            # 创建模型实例
            model = genai.GenerativeModel(request.model or self.default_model)
            
            # 转换消息格式
            prompt = self._convert_messages_to_prompt(request.messages)
            
            # 生成配置
            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                top_p=request.top_p,
                top_k=request.top_k
            )
            
            response_id = self._generate_response_id()
            
            # Gemini流式API
            response_stream = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    stream=True
                )
            )
            
            # 处理流式响应
            accumulated_text = ""
            for chunk in response_stream:
                if chunk.text:
                    accumulated_text += chunk.text
                    
                    yield UnifiedStreamChunk(
                        id=response_id,
                        model=request.model or self.default_model,
                        provider=self.provider_type.value,
                        choices=[{
                            "index": 0,
                            "delta": {"content": chunk.text},
                            "finish_reason": None
                        }]
                    )
            
            # 发送结束块
            yield UnifiedStreamChunk(
                id=response_id,
                model=request.model or self.default_model,
                provider=self.provider_type.value,
                choices=[{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            )
        
        except Exception as e:
            logger.error(f"Gemini流式聊天失败: {e}")
            yield UnifiedStreamChunk(
                id=self._generate_response_id(),
                model=request.model or self.default_model,
                provider=self.provider_type.value,
                choices=[{
                    "index": 0,
                    "delta": {"content": f"错误: {str(e)}"},
                    "finish_reason": "error"
                }]
            )
    
    async def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型列表"""
        models = []
        
        try:
            if not GEMINI_AVAILABLE:
                return models
            
            # 返回支持的模型
            for model_id in self.supported_models:
                models.append(ModelInfo(
                    id=model_id,
                    provider=self.provider_type.value,
                    engine=self.engine_type.value,
                    capabilities=["chat", "completion"],
                    context_length=self._get_context_length(model_id),
                    status="available"
                ))
        
        except Exception as e:
            logger.error(f"获取Gemini模型列表失败: {e}")
        
        return models
    
    async def health_check(self) -> Dict[str, Any]:
        """Gemini健康检查"""
        try:
            if not GEMINI_AVAILABLE:
                return {
                    "status": "unhealthy", 
                    "error": "Gemini SDK not available"
                }
            
            # 测试简单生成
            model = genai.GenerativeModel(self.default_model)
            
            test_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(
                    "Hello",
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=10
                    )
                )
            )
            
            if test_response.text:
                return {
                    "status": "healthy",
                    "provider": self.provider_type.value,
                    "default_model": self.default_model,
                    "models_available": len(self.supported_models),
                    "last_check": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Test generation failed"
                }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """将消息转换为Gemini prompt格式"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts)
    
    def _convert_from_gemini_format(self, response, request: UnifiedChatRequest, latency_ms: float) -> UnifiedChatResponse:
        """转换Gemini响应格式"""
        content = response.text if response.text else ""
        
        # 估算token数量
        prompt_tokens = self._estimate_tokens(self._convert_messages_to_prompt(request.messages))
        completion_tokens = self._estimate_tokens(content)
        total_tokens = prompt_tokens + completion_tokens
        
        # 计算tokens/second
        tokens_per_second = (total_tokens / latency_ms * 1000) if latency_ms > 0 and total_tokens > 0 else 0
        
        return UnifiedChatResponse(
            id=self._generate_response_id(),
            model=request.model or self.default_model,
            provider=self.provider_type.value,
            engine=self.engine_type.value,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            performance={
                "latency_ms": latency_ms,
                "tokens_per_second": tokens_per_second,
                "processing_time_ms": latency_ms
            }
        )
    
    def _get_context_length(self, model_id: str) -> int:
        """获取模型上下文长度"""
        context_lengths = {
            "gemini-1.5-pro": 2097152,  # 2M tokens
            "gemini-1.5-flash": 1048576,  # 1M tokens
            "gemini-pro": 32768,
            "gemini-pro-vision": 16384
        }
        
        return context_lengths.get(model_id, 32768)