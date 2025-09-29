"""
Anthropic Claude适配器
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


class ClaudeAdapter(BaseAdapter):
    """Anthropic Claude适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = ProviderType.CLAUDE
        self.engine_type = EngineType.CLOUD
        
        # 配置参数
        self.api_key = config.get("api_key")
        self.endpoint = config.get("endpoint", "https://api.anthropic.com")
        self.default_model = config.get("default_model", "claude-3-sonnet-20240229")
        self.timeout = config.get("timeout", 60)
        self.version = config.get("version", "2023-06-01")
        
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 支持的模型列表
        self.supported_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    async def initialize(self) -> bool:
        """初始化Claude适配器"""
        try:
            if not self.api_key:
                logger.error("Claude API密钥未配置")
                return False
            
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.version,
                    "Content-Type": "application/json"
                }
            )
            
            # 测试连接
            health_result = await self.health_check()
            self.healthy = health_result.get("status") == "healthy"
            self.initialized = True
            
            logger.info(f"Claude适配器初始化{'成功' if self.healthy else '失败'}")
            return self.healthy
            
        except Exception as e:
            logger.error(f"Claude适配器初始化失败: {e}")
            self.initialized = True
            self.healthy = False
            return False
    
    async def chat_completion(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """Claude聊天完成"""
        try:
            if not self.session:
                raise Exception("适配器未初始化")
            
            # 转换请求格式
            claude_request = self._convert_to_claude_format(request)
            
            # 发送请求
            start_time = datetime.now()
            async with self.session.post(
                f"{self.endpoint}/v1/messages",
                json=claude_request
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    # 计算性能指标
                    end_time = datetime.now()
                    latency_ms = (end_time - start_time).total_seconds() * 1000
                    
                    # 转换响应格式
                    return self._convert_from_claude_format(data, request, latency_ms)
                else:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get("message", "未知错误")
                    raise Exception(f"Claude API错误 ({response.status}): {error_msg}")
        
        except Exception as e:
            logger.error(f"Claude聊天完成失败: {e}")
            return self._format_error_response(str(e), request)
    
    async def chat_completion_stream(self, request: UnifiedChatRequest) -> AsyncGenerator[UnifiedStreamChunk, None]:
        """Claude流式聊天完成"""
        try:
            if not self.session:
                raise Exception("适配器未初始化")
            
            # 转换请求格式并启用流式
            claude_request = self._convert_to_claude_format(request)
            claude_request["stream"] = True
            
            async with self.session.post(
                f"{self.endpoint}/v1/messages",
                json=claude_request
            ) as response:
                
                if response.status != 200:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get("message", "未知错误")
                    raise Exception(f"Claude API错误 ({response.status}): {error_msg}")
                
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
            logger.error(f"Claude流式聊天失败: {e}")
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
        
        for model_id in self.supported_models:
            models.append(ModelInfo(
                id=model_id,
                provider=self.provider_type.value,
                engine=self.engine_type.value,
                capabilities=["chat", "completion"],
                context_length=self._get_context_length(model_id),
                status="available"
            ))
        
        return models
    
    async def health_check(self) -> Dict[str, Any]:
        """Claude健康检查"""
        try:
            if not self.session:
                return {"status": "unhealthy", "error": "session not initialized"}
            
            # 测试简单请求
            test_request = {
                "model": self.default_model,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            async with self.session.post(
                f"{self.endpoint}/v1/messages",
                json=test_request
            ) as response:
                
                if response.status == 200:
                    return {
                        "status": "healthy",
                        "provider": self.provider_type.value,
                        "endpoint": self.endpoint,
                        "default_model": self.default_model,
                        "models_available": len(self.supported_models),
                        "last_check": datetime.now().isoformat()
                    }
                else:
                    error_data = await response.json()
                    return {
                        "status": "unhealthy",
                        "error": f"API返回状态码 {response.status}: {error_data}",
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
        logger.info("Claude适配器资源已清理")
    
    def _convert_to_claude_format(self, request: UnifiedChatRequest) -> Dict[str, Any]:
        """转换为Claude请求格式"""
        # Claude需要提取system消息
        system_message = ""
        messages = []
        
        for msg in request.messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                messages.append(msg)
        
        claude_request = {
            "model": request.model or self.default_model,
            "max_tokens": request.max_tokens or 1024,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "messages": messages
        }
        
        if system_message:
            claude_request["system"] = system_message
        
        # 移除None值
        return {k: v for k, v in claude_request.items() if v is not None}
    
    def _convert_from_claude_format(self, data: Dict[str, Any], request: UnifiedChatRequest, latency_ms: float) -> UnifiedChatResponse:
        """转换Claude响应格式"""
        content = ""
        if data.get("content") and len(data["content"]) > 0:
            content = data["content"][0].get("text", "")
        
        usage = data.get("usage", {})
        
        # 计算tokens/second
        total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        tokens_per_second = (total_tokens / latency_ms * 1000) if latency_ms > 0 and total_tokens > 0 else 0
        
        return UnifiedChatResponse(
            id=data.get("id", self._generate_response_id()),
            model=data.get("model", request.model or self.default_model),
            provider=self.provider_type.value,
            engine=self.engine_type.value,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": data.get("stop_reason", "stop")
            }],
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": total_tokens
            },
            performance={
                "latency_ms": latency_ms,
                "tokens_per_second": tokens_per_second,
                "processing_time_ms": latency_ms
            }
        )
    
    def _convert_stream_chunk(self, data: Dict[str, Any], response_id: str, request: UnifiedChatRequest) -> Optional[UnifiedStreamChunk]:
        """转换流式响应块"""
        if data.get("type") == "content_block_delta":
            delta_data = data.get("delta", {})
            text = delta_data.get("text", "")
            
            if text:
                return UnifiedStreamChunk(
                    id=response_id,
                    model=request.model or self.default_model,
                    provider=self.provider_type.value,
                    choices=[{
                        "index": 0,
                        "delta": {"content": text},
                        "finish_reason": None
                    }]
                )
        
        elif data.get("type") == "message_stop":
            return UnifiedStreamChunk(
                id=response_id,
                model=request.model or self.default_model,
                provider=self.provider_type.value,
                choices=[{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            )
        
        return None
    
    def _get_context_length(self, model_id: str) -> int:
        """获取模型上下文长度"""
        context_lengths = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000
        }
        
        return context_lengths.get(model_id, 100000)