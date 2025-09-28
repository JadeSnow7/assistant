"""
本地模型适配器 - 支持llama.cpp和Ollama
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


class LlamaCppAdapter(BaseAdapter):
    """llama.cpp适配器 - 通过gRPC与C++引擎通信"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = ProviderType.LLAMACPP
        self.engine_type = EngineType.LOCAL
        
        # 配置参数
        self.grpc_client = config.get("grpc_client")
        self.model_path = config.get("model_path", "./models")
        self.default_model = config.get("default_model", "qwen3:4b")
        self.gpu_layers = config.get("gpu_layers", 35)
        self.threads = config.get("threads", 8)
        self.context_length = config.get("context_length", 4096)
        
        # 可用模型列表
        self.available_models = [
            "qwen3:4b",
            "qwen2.5:7b", 
            "deepseek:7b",
            "llama3:8b",
            "llama3.1:8b",
            "codellama:7b"
        ]
    
    async def initialize(self) -> bool:
        """初始化llama.cpp适配器"""
        try:
            if not self.grpc_client:
                logger.error("gRPC客户端未配置")
                return False
            
            # 测试gRPC连接
            health_result = await self.health_check()
            self.healthy = health_result.get("status") == "healthy"
            self.initialized = True
            
            logger.info(f"llama.cpp适配器初始化{'成功' if self.healthy else '失败'}")
            return self.healthy
            
        except Exception as e:
            logger.error(f"llama.cpp适配器初始化失败: {e}")
            self.initialized = True
            self.healthy = False
            return False
    
    async def chat_completion(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """llama.cpp聊天完成"""
        try:
            if not self.grpc_client:
                raise Exception("gRPC客户端未配置")
            
            # 转换消息格式为prompt
            prompt = self._format_chat_prompt(request.messages)
            
            # 调用C++引擎
            start_time = datetime.now()
            
            response = await self.grpc_client.inference(
                prompt=prompt,
                model_type="chat",
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature or 0.7,
                top_p=request.top_p or 0.9,
                top_k=request.top_k or 40
            )
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # 转换响应格式
            return self._convert_from_cpp_format(response, request, latency_ms)
        
        except Exception as e:
            logger.error(f"llama.cpp聊天完成失败: {e}")
            return self._format_error_response(str(e), request)
    
    async def chat_completion_stream(self, request: UnifiedChatRequest) -> AsyncGenerator[UnifiedStreamChunk, None]:
        """llama.cpp流式聊天完成"""
        try:
            if not self.grpc_client:
                raise Exception("gRPC客户端未配置")
            
            # 转换消息格式为prompt
            prompt = self._format_chat_prompt(request.messages)
            
            response_id = self._generate_response_id()
            
            # 调用C++引擎流式接口
            async for chunk in self.grpc_client.inference_stream(
                prompt=prompt,
                model_type="chat",
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature or 0.7,
                top_p=request.top_p or 0.9,
                top_k=request.top_k or 40
            ):
                if chunk.get("text"):
                    yield UnifiedStreamChunk(
                        id=response_id,
                        model=request.model or self.default_model,
                        provider=self.provider_type.value,
                        choices=[{
                            "index": 0,
                            "delta": {"content": chunk["text"]},
                            "finish_reason": None
                        }]
                    )
                
                if chunk.get("finished", False):
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
                    break
        
        except Exception as e:
            logger.error(f"llama.cpp流式聊天失败: {e}")
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
            # 从gRPC客户端获取模型列表
            if self.grpc_client:
                grpc_models = await self.grpc_client.get_available_models()
                
                for model_name in grpc_models:
                    models.append(ModelInfo(
                        id=model_name,
                        provider=self.provider_type.value,
                        engine=self.engine_type.value,
                        capabilities=["chat", "completion", "embedding"],
                        context_length=self.context_length,
                        status="available"
                    ))
            else:
                # 返回配置的模型列表
                for model_name in self.available_models:
                    models.append(ModelInfo(
                        id=model_name,
                        provider=self.provider_type.value,
                        engine=self.engine_type.value,
                        capabilities=["chat", "completion"],
                        context_length=self.context_length,
                        status="available"
                    ))
        
        except Exception as e:
            logger.error(f"获取llama.cpp模型列表失败: {e}")
        
        return models
    
    async def health_check(self) -> Dict[str, Any]:
        """llama.cpp健康检查"""
        try:
            if not self.grpc_client:
                return {"status": "unhealthy", "error": "gRPC client not configured"}
            
            # 测试gRPC连接
            system_info = await self.grpc_client.get_system_info()
            
            if system_info:
                return {
                    "status": "healthy",
                    "provider": self.provider_type.value,
                    "engine": self.engine_type.value,
                    "default_model": self.default_model,
                    "context_length": self.context_length,
                    "gpu_layers": self.gpu_layers,
                    "system_info": system_info,
                    "last_check": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "gRPC connection failed"
                }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """格式化为适合llama.cpp的prompt"""
        formatted_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                formatted_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
            elif role == "user":
                formatted_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
            elif role == "assistant":
                formatted_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
        
        # 添加assistant提示符等待响应
        formatted_parts.append("<|im_start|>assistant\n")
        
        return "\n".join(formatted_parts)
    
    def _convert_from_cpp_format(self, response: Dict[str, Any], request: UnifiedChatRequest, latency_ms: float) -> UnifiedChatResponse:
        """转换C++响应格式"""
        content = response.get("text", "")
        
        # 计算token统计
        prompt_tokens = self._estimate_tokens(self._format_chat_prompt(request.messages))
        completion_tokens = response.get("token_count", self._estimate_tokens(content))
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
                "processing_time_ms": response.get("latency_ms", latency_ms)
            }
        )


class OllamaAdapter(BaseAdapter):
    """Ollama适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = ProviderType.OLLAMA
        self.engine_type = EngineType.LOCAL
        
        # 配置参数
        self.endpoint = config.get("endpoint", "http://localhost:11434")
        self.default_model = config.get("default_model", "qwen2.5:4b")
        self.timeout = config.get("timeout", 60)
        
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """初始化Ollama适配器"""
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 测试连接
            health_result = await self.health_check()
            self.healthy = health_result.get("status") == "healthy"
            self.initialized = True
            
            logger.info(f"Ollama适配器初始化{'成功' if self.healthy else '失败'}")
            return self.healthy
            
        except Exception as e:
            logger.error(f"Ollama适配器初始化失败: {e}")
            self.initialized = True
            self.healthy = False
            return False
    
    async def chat_completion(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """Ollama聊天完成"""
        try:
            if not self.session:
                raise Exception("适配器未初始化")
            
            # 构建Ollama请求
            ollama_request = {
                "model": request.model or self.default_model,
                "messages": request.messages,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "top_k": request.top_k,
                    "num_predict": request.max_tokens
                }
            }
            
            # 发送请求
            start_time = datetime.now()
            async with self.session.post(
                f"{self.endpoint}/api/chat",
                json=ollama_request
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    end_time = datetime.now()
                    latency_ms = (end_time - start_time).total_seconds() * 1000
                    
                    return self._convert_from_ollama_format(data, request, latency_ms)
                else:
                    error_text = await response.text()
                    raise Exception(f"Ollama API错误 ({response.status}): {error_text}")
        
        except Exception as e:
            logger.error(f"Ollama聊天完成失败: {e}")
            return self._format_error_response(str(e), request)
    
    async def chat_completion_stream(self, request: UnifiedChatRequest) -> AsyncGenerator[UnifiedStreamChunk, None]:
        """Ollama流式聊天完成"""
        try:
            if not self.session:
                raise Exception("适配器未初始化")
            
            # 构建Ollama流式请求
            ollama_request = {
                "model": request.model or self.default_model,
                "messages": request.messages,
                "stream": True,
                "options": {
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "top_k": request.top_k,
                    "num_predict": request.max_tokens
                }
            }
            
            response_id = self._generate_response_id()
            
            async with self.session.post(
                f"{self.endpoint}/api/chat",
                json=ollama_request
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API错误 ({response.status}): {error_text}")
                
                # 处理流式响应
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line:
                        try:
                            data = json.loads(line)
                            
                            message = data.get("message", {})
                            content = message.get("content", "")
                            
                            if content:
                                yield UnifiedStreamChunk(
                                    id=response_id,
                                    model=request.model or self.default_model,
                                    provider=self.provider_type.value,
                                    choices=[{
                                        "index": 0,
                                        "delta": {"content": content},
                                        "finish_reason": None
                                    }]
                                )
                            
                            if data.get("done", False):
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
                                break
                        
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            logger.error(f"Ollama流式聊天失败: {e}")
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
        """获取Ollama可用模型列表"""
        models = []
        
        try:
            if not self.session:
                return models
            
            async with self.session.get(f"{self.endpoint}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for model_data in data.get("models", []):
                        model_name = model_data.get("name", "")
                        
                        models.append(ModelInfo(
                            id=model_name,
                            provider=self.provider_type.value,
                            engine=self.engine_type.value,
                            capabilities=["chat", "completion"],
                            context_length=8192,  # Ollama默认上下文长度
                            status="available"
                        ))
        
        except Exception as e:
            logger.error(f"获取Ollama模型列表失败: {e}")
        
        return models
    
    async def health_check(self) -> Dict[str, Any]:
        """Ollama健康检查"""
        try:
            if not self.session:
                return {"status": "unhealthy", "error": "session not initialized"}
            
            async with self.session.get(f"{self.endpoint}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    
                    return {
                        "status": "healthy",
                        "provider": self.provider_type.value,
                        "endpoint": self.endpoint,
                        "models_available": len(models),
                        "default_model": self.default_model,
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
        logger.info("Ollama适配器资源已清理")
    
    def _convert_from_ollama_format(self, data: Dict[str, Any], request: UnifiedChatRequest, latency_ms: float) -> UnifiedChatResponse:
        """转换Ollama响应格式"""
        message = data.get("message", {})
        content = message.get("content", "")
        
        # 估算token数量
        prompt_tokens = sum(self._estimate_tokens(msg.get("content", "")) for msg in request.messages)
        completion_tokens = self._estimate_tokens(content)
        total_tokens = prompt_tokens + completion_tokens
        
        # 计算tokens/second
        tokens_per_second = (total_tokens / latency_ms * 1000) if latency_ms > 0 and total_tokens > 0 else 0
        
        return UnifiedChatResponse(
            id=self._generate_response_id(),
            model=data.get("model", request.model or self.default_model),
            provider=self.provider_type.value,
            engine=self.engine_type.value,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop" if data.get("done", False) else "length"
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