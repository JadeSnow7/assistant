"""
Ollama本地模型客户端
"""
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from core.config import settings


logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama本地模型客户端"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_models: List[str] = []
        self.default_model = "qwen3:4b"  # 使用您已经拉取的qwen3:4b模型
        self.initialized = False
    
    async def initialize(self):
        """初始化Ollama客户端"""
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=300)  # 5分钟超时，因为本地推理可能较慢
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 检查Ollama服务状态
            await self._check_ollama_status()
            
            # 获取可用模型列表
            await self._update_available_models()
            
            self.initialized = True
            logger.info(f"Ollama客户端初始化成功，可用模型: {self.available_models}")
            
        except Exception as e:
            logger.error(f"Ollama客户端初始化失败: {e}")
            self.initialized = False
            raise
    
    async def _check_ollama_status(self):
        """检查Ollama服务状态"""
        try:
            async with self.session.get(f"{self.base_url}/api/version") as response:
                if response.status == 200:
                    version_info = await response.json()
                    logger.info(f"Ollama服务正常，版本: {version_info.get('version', 'unknown')}")
                    return True
                else:
                    raise Exception(f"Ollama服务响应异常: {response.status}")
        except Exception as e:
            logger.error(f"Ollama服务检查失败: {e}")
            raise Exception("Ollama服务不可用，请确保Ollama已启动")
    
    async def _update_available_models(self):
        """更新可用模型列表"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    self.available_models = [model.get("name", "") for model in models if model.get("name")]
                    
                    # 检查默认模型是否存在
                    if self.default_model not in self.available_models:
                        if "qwen3:4b" in self.available_models:
                            self.default_model = "qwen3:4b"
                        elif "qwen2.5:4b" in self.available_models:
                            self.default_model = "qwen2.5:4b"
                        elif "qwen:4b" in self.available_models:
                            self.default_model = "qwen:4b"
                        elif self.available_models:
                            self.default_model = self.available_models[0]
                            logger.warning(f"默认模型不存在，使用: {self.default_model}")
                        else:
                            raise Exception("没有找到可用的模型")
                    
                    logger.info(f"默认使用模型: {self.default_model}")
                else:
                    raise Exception(f"获取模型列表失败: {response.status}")
        except Exception as e:
            logger.error(f"更新模型列表失败: {e}")
            raise
    
    async def chat_completion(self, 
                             messages: List[Dict[str, str]],
                             model: str = None,
                             max_tokens: int = 1024,
                             temperature: float = 0.7,
                             stream: bool = False) -> Dict[str, Any]:
        """聊天完成API"""
        if not self.initialized:
            raise Exception("Ollama客户端未初始化")
        
        model = model or self.default_model
        
        # 转换消息格式为单个prompt
        prompt = self._convert_messages_to_prompt(messages)
        
        try:
            start_time = datetime.now()
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_k": 40,
                    "top_p": 0.9,
                }
            }
            
            if stream:
                return await self._stream_generate(payload, start_time)
            else:
                return await self._generate(payload, start_time)
                
        except Exception as e:
            logger.error(f"Ollama聊天完成失败: {e}")
            return {
                "error": str(e),
                "content": "抱歉，本地模型暂时不可用，请稍后重试。"
            }
    
    async def _generate(self, payload: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """非流式生成"""
        async with self.session.post(f"{self.base_url}/api/generate", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                end_time = datetime.now()
                latency_ms = (end_time - start_time).total_seconds() * 1000
                
                content = data.get("response", "")
                
                return {
                    "content": content,
                    "model": payload["model"],
                    "latency_ms": latency_ms,
                    "token_count": len(content.split()),  # 简单估算
                    "finish_reason": "stop" if data.get("done", False) else "length"
                }
            else:
                error_text = await response.text()
                raise Exception(f"API调用失败: {response.status} - {error_text}")
    
    async def _stream_generate(self, payload: Dict[str, Any], start_time: datetime) -> AsyncGenerator[Dict[str, Any], None]:
        """流式生成"""
        async with self.session.post(f"{self.base_url}/api/generate", json=payload) as response:
            if response.status == 200:
                full_content = ""
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            
                            if "response" in data:
                                chunk_content = data["response"]
                                full_content += chunk_content
                                
                                yield {
                                    "content": chunk_content,
                                    "finished": data.get("done", False),
                                    "model": payload["model"]
                                }
                            
                            if data.get("done", False):
                                end_time = datetime.now()
                                latency_ms = (end_time - start_time).total_seconds() * 1000
                                
                                yield {
                                    "content": "",
                                    "finished": True,
                                    "model": payload["model"],
                                    "latency_ms": latency_ms,
                                    "token_count": len(full_content.split()),
                                    "finish_reason": "stop"
                                }
                                break
                                
                        except json.JSONDecodeError:
                            continue
            else:
                error_text = await response.text()
                yield {
                    "error": f"API调用失败: {response.status} - {error_text}",
                    "content": "抱歉，本地模型调用失败。"
                }
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """将对话消息转换为单个prompt"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # 添加最终的Assistant提示
        if not prompt_parts or not prompt_parts[-1].startswith("Assistant:"):
            prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if not self.initialized:
            await self.initialize()
        return self.available_models.copy()
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """拉取模型"""
        try:
            payload = {"name": model_name}
            
            async with self.session.post(f"{self.base_url}/api/pull", json=payload) as response:
                if response.status == 200:
                    # 等待拉取完成
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                if data.get("status") == "success":
                                    await self._update_available_models()
                                    return {"success": True, "message": f"模型 {model_name} 拉取成功"}
                            except json.JSONDecodeError:
                                continue
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"拉取失败: {error_text}"}
        except Exception as e:
            logger.error(f"拉取模型失败: {e}")
            return {"success": False, "error": str(e)}
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return (
            self.initialized and 
            self.session is not None and 
            not self.session.closed and
            len(self.available_models) > 0
        )
    
    async def cleanup(self):
        """清理资源"""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("Ollama客户端资源已清理")