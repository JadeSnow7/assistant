"""
云端API客户端 - 支持Google Gemini和OpenAI
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from core.config import settings


logger = logging.getLogger(__name__)


class CloudClient:
    """云端API客户端 - 支持Google Gemini和OpenAI"""
    
    def __init__(self):
        # 基础配置
        self.session: Optional[aiohttp.ClientSession] = None
        self.initialized = False
        
        # Gemini配置
        self.gemini_api_key = settings.gemini_api_key
        self.gemini_model = settings.gemini_model
        self.gemini_generation_config = settings.gemini_generation_config
        self.gemini_client = None
        
        # OpenAI配置
        self.openai_api_key = settings.cloud_api_key
        self.openai_endpoint = settings.cloud_api_endpoint
        
        # 模型类型
        self.model_type = settings.cloud_model_type
        
        # 支持的模型列表
        self.available_models = {
            "gemini": [
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-pro"
            ],
            "openai": [
                "gpt-4",
                "gpt-4-turbo", 
                "gpt-3.5-turbo"
            ]
        }
    
    async def initialize(self):
        """初始化云端客户端"""
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 初始化Gemini客户端
            if self.gemini_api_key and GEMINI_AVAILABLE:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_client = genai.GenerativeModel(self.gemini_model)
                logger.info(f"初始化Gemini模型: {self.gemini_model}")
                
                # 测试Gemini连接
                await self._test_gemini_connection()
            
            # 测试OpenAI连接（如果有API密钥）
            elif self.openai_api_key and self.model_type == "openai":
                await self._test_openai_connection()
            
            self.initialized = True
            logger.info("云端API客户端初始化完成")
            
        except Exception as e:
            logger.error(f"云端API客户端初始化失败: {e}")
            self.initialized = True  # 即使失败也标记为初始化，允许后续重试
    
    async def chat_completion(self, 
                             messages: List[Dict[str, str]],
                             model: str = "gemini-1.5-pro",
                             max_tokens: int = 1024,
                             temperature: float = 0.7) -> Dict[str, Any]:
        """聊天完成API调用 - 支持Gemini和OpenAI"""
        try:
            if not self.session:
                await self.initialize()
            
            # 根据模型类型选择API
            if model.startswith("gemini") or (self.gemini_api_key and self.model_type == "gemini"):
                return await self._gemini_chat_completion(messages, model, max_tokens, temperature)
            else:
                return await self._openai_chat_completion(messages, model, max_tokens, temperature)
                
        except Exception as e:
            logger.error(f"云端API调用异常: {e}")
            return {
                "error": str(e),
                "content": "抱歉，云端服务出现异常，请稍后重试。"
            }
    
    async def _gemini_chat_completion(self, 
                                    messages: List[Dict[str, str]],
                                    model: str,
                                    max_tokens: int,
                                    temperature: float) -> Dict[str, Any]:
        """使用Google Gemini API进行聊天完成"""
        try:
            if not self.gemini_api_key:
                return {
                    "error": "未配置Gemini API密钥",
                    "content": "抱歉，云端服务暂不可用，请配置Gemini API密钥。"
                }
            
            if not GEMINI_AVAILABLE:
                return {
                    "error": "Gemini SDK不可用",
                    "content": "请安装google-generativeai包。"
                }
            
            # 转换消息格式
            prompt = self._convert_messages_to_prompt(messages)
            
            # 生成配置
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=self.gemini_generation_config.get("top_p", 0.8),
                top_k=self.gemini_generation_config.get("top_k", 40)
            )
            
            # 调用Gemini API
            start_time = datetime.now()
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini_client.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            )
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # 解析响应
            if response.parts:
                content = response.text
                
                # 估算token数（Gemini不直接提供token计数）
                token_count = len(content.split()) + len(prompt.split())
                
                return {
                    "content": content,
                    "model": model,
                    "token_count": token_count,
                    "latency_ms": latency_ms,
                    "finish_reason": "stop"
                }
            else:
                logger.error("Gemini返回空响应")
                return {
                    "error": "Gemini返回空响应",
                    "content": "抱歉，模型没有生成响应，请重试。"
                }
                
        except Exception as e:
            logger.error(f"Gemini API调用异常: {e}")
            return {
                "error": str(e),
                "content": "抱歉，Gemini服务出现异常，请稍后重试。"
            }
    
    async def _openai_chat_completion(self, 
                                    messages: List[Dict[str, str]],
                                    model: str,
                                    max_tokens: int,
                                    temperature: float) -> Dict[str, Any]:
        """使用OpenAI API进行聊天完成"""
        try:
            if not self.openai_api_key:
                return {
                    "error": "未配置OpenAI API密钥",
                    "content": "抱歉，云端服务暂不可用，请配置OpenAI API密钥。"
                }
            
            # 构建请求
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # 发送请求
            start_time = datetime.now()
            
            async with self.session.post(
                f"{self.openai_endpoint}/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    # 解析响应
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    content = message.get("content", "")
                    
                    # 计算统计信息
                    end_time = datetime.now()
                    latency_ms = (end_time - start_time).total_seconds() * 1000
                    
                    usage = data.get("usage", {})
                    token_count = usage.get("total_tokens", 0)
                    
                    return {
                        "content": content,
                        "model": data.get("model", model),
                        "token_count": token_count,
                        "latency_ms": latency_ms,
                        "finish_reason": choice.get("finish_reason", "stop")
                    }
                    
                else:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get("message", "未知错误")
                    
                    logger.error(f"OpenAI API调用失败: {response.status} - {error_msg}")
                    
                    return {
                        "error": f"API调用失败: {error_msg}",
                        "content": "抱歉，云端服务暂时不可用，请稍后重试。"
                    }
                    
        except asyncio.TimeoutError:
            logger.error("OpenAI API调用超时")
            return {
                "error": "API调用超时",
                "content": "抱歉，云端服务响应超时，请稍后重试。"
            }
            
        except Exception as e:
            logger.error(f"OpenAI API调用异常: {e}")
            return {
                "error": str(e),
                "content": "抱歉，OpenAI服务出现异常，请稍后重试。"
            }
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """将OpenAI消息格式转换为Gemini的prompt格式"""
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
    
    async def _test_gemini_connection(self):
        """测试Gemini API连接"""
        try:
            test_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini_client.generate_content(
                    "Hello",
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=10
                    )
                )
            )
            
            if test_response.parts:
                logger.info("Gemini API连接测试成功")
                return True
            else:
                logger.warning("Gemini API连接测试失败：无响应")
                return False
                
        except Exception as e:
            logger.warning(f"Gemini API连接测试异常: {e}")
            return False
    
    async def _test_openai_connection(self):
        """测试OpenAI API连接"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            async with self.session.get(
                f"{self.openai_endpoint}/models",
                headers=headers
            ) as response:
                
                if response.status == 200:
                    logger.info("OpenAI API连接测试成功")
                    return True
                else:
                    logger.warning(f"OpenAI API连接测试失败: {response.status}")
                    return False
                    
        except Exception as e:
            logger.warning(f"OpenAI API连接测试异常: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        models = []
        
        if self.gemini_api_key and GEMINI_AVAILABLE:
            models.extend(self.available_models["gemini"])
        
        if self.openai_api_key:
            models.extend(self.available_models["openai"])
        
        return models
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return (
            self.initialized and 
            self.session is not None and 
            not self.session.closed
        )
    
    async def cleanup(self):
        """清理资源"""
        if self.session and not self.session.closed:
            await self.session.close()
        
        logger.info("云端API客户端资源已清理")