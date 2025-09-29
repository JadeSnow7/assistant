"""
OpenAI兼容适配器 - 支持OpenAI API和兼容接口
"""
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from .base import (
    BaseAdapter, UnifiedChatRequest, UnifiedChatResponse, 
    UnifiedStreamChunk, ModelInfo, ProviderType, EngineType
)


logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    """OpenAI API适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = ProviderType.OPENAI
        self.engine_type = EngineType.CLOUD
        
        # 配置参数
        self.api_key = config.get("api_key")
        self.endpoint = config.get("endpoint", "https://api.openai.com/v1")
        self.default_model = config.get("default_model", "gpt-3.5-turbo")
        self.rate_limit = config.get("rate_limit", 3000)
        self.timeout = config.get("timeout", 60)
        
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 支持的模型列表
        self.supported_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview", 
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]
    
    async def initialize(self) -> bool:
        """初始化OpenAI适配器"""
        try:
            if not self.api_key:
                logger.error("OpenAI API密钥未配置")
                return False
            
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            # 测试连接
            health_result = await self.health_check()
            self.healthy = health_result.get("status") == "healthy"
            self.initialized = True
            
            logger.info(f"OpenAI适配器初始化{'成功' if self.healthy else '失败'}")
            return self.healthy
            
        except Exception as e:
            logger.error(f"OpenAI适配器初始化失败: {e}")
            self.initialized = True  # 标记为已初始化但不健康
            self.healthy = False
            return False
    
    async def chat_completion(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """OpenAI聊天完成"""
        try:
            if not self.session:
                raise Exception("适配器未初始化")
            
            # 转换请求格式
            openai_request = self._convert_to_openai_format(request)
            
            # 发送请求
            start_time = datetime.now()
            async with self.session.post(
                f"{self.endpoint}/chat/completions",
                json=openai_request
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    # 计算性能指标
                    end_time = datetime.now()
                    latency_ms = (end_time - start_time).total_seconds() * 1000
                    
                    # 转换响应格式
                    return self._convert_from_openai_format(data, request, latency_ms)
                else:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get("message", "未知错误")
                    raise Exception(f"OpenAI API错误 ({response.status}): {error_msg}")
        
        except Exception as e:
            logger.error(f"OpenAI聊天完成失败: {e}")
            return self._format_error_response(str(e), request)
    
    async def chat_completion_stream(self, request: UnifiedChatRequest) -> AsyncGenerator[UnifiedStreamChunk, None]:
        """OpenAI流式聊天完成"""
        try:
            if not self.session:
                raise Exception("适配器未初始化")
            
            # 转换请求格式并启用流式
            openai_request = self._convert_to_openai_format(request)
            openai_request["stream"] = True
            
            async with self.session.post(
                f"{self.endpoint}/chat/completions",
                json=openai_request
            ) as response:
                
                if response.status != 200:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get("message", "未知错误")
                    raise Exception(f"OpenAI API错误 ({response.status}): {error_msg}")
                
                # 处理流式响应
                response_id = self._generate_response_id()
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith("data: "):
                        data_str = line[6:]  # 移除 "data: " 前缀
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            chunk = self._convert_stream_chunk(data, response_id, request)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            logger.error(f"OpenAI流式聊天失败: {e}")
            # 返回错误块
            yield UnifiedStreamChunk(
                id=self._generate_response_id(),
                model=request.model,
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
            if not self.session:
                return models
            
            # 获取OpenAI模型列表
            async with self.session.get(f"{self.endpoint}/models") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for model_data in data.get("data", []):
                        model_id = model_data.get("id", "")
                        
                        # 只返回聊天模型
                        if any(supported in model_id for supported in self.supported_models):
                            models.append(ModelInfo(
                                id=model_id,
                                provider=self.provider_type.value,
                                engine=self.engine_type.value,
                                capabilities=["chat", "completion"],
                                context_length=self._get_context_length(model_id),
                                status="available"
                            ))
        
        except Exception as e:
            logger.error(f"获取OpenAI模型列表失败: {e}")
        
        return models
    
    async def health_check(self) -> Dict[str, Any]:
        """OpenAI健康检查"""
        try:
            if not self.session:
                return {"status": "unhealthy", "error": "session not initialized"}
            
            # 测试连接
            async with self.session.get(f"{self.endpoint}/models") as response:
                if response.status == 200:
                    return {
                        "status": "healthy",
                        "provider": self.provider_type.value,
                        "endpoint": self.endpoint,
                        "models_available": len(self.supported_models),
                        "last_check": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy", 
                        "error": f"API返回状态码 {response.status}",
                        "endpoint": self.endpoint
                    }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "endpoint": self.endpoint
            }
    
    async def cleanup(self):
        """清理资源"""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("OpenAI适配器资源已清理")
    
    def _convert_to_openai_format(self, request: UnifiedChatRequest) -> Dict[str, Any]:
        """转换为OpenAI请求格式"""
        openai_request = {
            "model": request.model or self.default_model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": request.stream
        }
        
        # 移除None值
        return {k: v for k, v in openai_request.items() if v is not None}
    
    def _convert_from_openai_format(self, data: Dict[str, Any], request: UnifiedChatRequest, latency_ms: float) -> UnifiedChatResponse:
        """转换OpenAI响应格式"""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})
        
        # 计算tokens/second
        total_tokens = usage.get("total_tokens", 0)
        tokens_per_second = (total_tokens / latency_ms * 1000) if latency_ms > 0 and total_tokens > 0 else 0
        
        return UnifiedChatResponse(
            id=data.get("id", self._generate_response_id()),
            model=data.get("model", request.model),
            provider=self.provider_type.value,
            engine=self.engine_type.value,
            choices=[{
                "index": choice.get("index", 0),
                "message": {
                    "role": message.get("role", "assistant"),
                    "content": message.get("content", "")
                },
                "finish_reason": choice.get("finish_reason", "stop")
            }],
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            },
            performance={
                "latency_ms": latency_ms,
                "tokens_per_second": tokens_per_second,
                "processing_time_ms": latency_ms
            }
        )
    
    def _convert_stream_chunk(self, data: Dict[str, Any], response_id: str, request: UnifiedChatRequest) -> Optional[UnifiedStreamChunk]:
        """转换流式响应块"""
        if not data.get("choices"):
            return None
        
        choice = data["choices"][0]
        delta = choice.get("delta", {})
        
        return UnifiedStreamChunk(
            id=response_id,
            model=data.get("model", request.model),
            provider=self.provider_type.value,
            choices=[{
                "index": choice.get("index", 0),
                "delta": delta,
                "finish_reason": choice.get("finish_reason")
            }]
        )
    
    def _get_context_length(self, model_id: str) -> int:
        """获取模型上下文长度"""
        context_lengths = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384
        }
        
        for model, length in context_lengths.items():
            if model in model_id:
                return length
        
        return 4096  # 默认值