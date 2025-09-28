"""
gRPC客户端 - 与C++核心层通信
"""
import grpc
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.schemas import SystemInfo
from core.config import settings
from core.ollama_client import OllamaClient


logger = logging.getLogger(__name__)


class GRPCClient:
    """gRPC客户端封装"""
    
    def __init__(self, server_address: str = None):
        self.server_address = server_address or settings.grpc_server_address
        self.channel: Optional[grpc.aio.Channel] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # 集成Ollama客户端用于本地推理
        self.ollama_client = OllamaClient()
    
    async def connect(self):
        """连接到gRPC服务器"""
        try:
            # 初始化Ollama客户端
            await self.ollama_client.initialize()
            
            # 模拟连接gRPC服务器（实际项目中这里会真正连接C++服务）
            # self.channel = grpc.aio.insecure_channel(self.server_address)
            
            # 测试连接
            await self.health_check()
            self.connected = True
            self.reconnect_attempts = 0
            
            logger.info(f"gRPC客户端已连接到 {self.server_address}（集成Ollama）")
            
        except Exception as e:
            logger.error(f"gRPC连接失败: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """断开连接"""
        if self.ollama_client:
            await self.ollama_client.cleanup()
            
        if self.channel:
            await self.channel.close()
            
        self.connected = False
        logger.info("gRPC连接已断开")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.channel:
                return False
            
            # 模拟健康检查调用
            # 实际实现中这里会调用C++服务的健康检查接口
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            return True
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    async def inference(self, 
                       prompt: str, 
                       model_type: str = "chat",
                       max_tokens: int = 1024,
                       temperature: float = 0.7) -> Dict[str, Any]:
        """模型推理调用 - 使用Ollama本地模型"""
        try:
            if not self.connected:
                await self._ensure_connected()
            
            # 使用Ollama进行本地推理
            messages = [{"role": "user", "content": prompt}]
            
            response = await self.ollama_client.chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            
            if "error" in response:
                raise Exception(response["error"])
            
            return {
                "text": response["content"],
                "finished": True,
                "confidence": 0.9,  # Ollama返回高置信度
                "used_model": response.get("model", "qwen2.5:4b"),
                "token_count": response.get("token_count", 0),
                "latency_ms": response.get("latency_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"推理调用失败: {e}")
            raise
    
    async def get_system_info(self) -> SystemInfo:
        """获取系统信息"""
        try:
            if not self.connected:
                await self._ensure_connected()
            
            # 模拟系统信息获取
            # 实际实现中调用C++系统管理模块
            await asyncio.sleep(0.1)
            
            return SystemInfo(
                cpu_usage=45.5,
                memory_usage=62.3,
                memory_total_gb=16.0,
                memory_free_gb=6.0,
                disk_usage=78.2,
                disk_free_gb=120.5,
                gpu_usage=23.1,
                gpu_memory_usage=15.8,
                cpu_cores=8,
                os_info="Linux 5.4.0-Ubuntu",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            raise
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        try:
            if not self.connected:
                await self._ensure_connected()
            
            # 返回Ollama中的可用模型
            models = await self.ollama_client.get_available_models()
            return models
            
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
    
    async def load_model(self, model_path: str) -> bool:
        """加载模型"""
        try:
            if not self.connected:
                await self._ensure_connected()
            
            logger.info(f"正在加载模型: {model_path}")
            
            # 模拟模型加载时间
            await asyncio.sleep(2.0)
            
            logger.info(f"模型加载完成: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False
    
    async def unload_model(self, model_name: str) -> bool:
        """卸载模型"""
        try:
            if not self.connected:
                await self._ensure_connected()
            
            logger.info(f"正在卸载模型: {model_name}")
            await asyncio.sleep(0.5)
            logger.info(f"模型卸载完成: {model_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"模型卸载失败: {e}")
            return False
    
    async def get_plugin_capabilities(self) -> List[str]:
        """获取C++插件能力"""
        try:
            if not self.connected:
                await self._ensure_connected()
            
            # 模拟C++插件能力
            return [
                "file_operations",
                "system_monitoring", 
                "network_tools",
                "audio_processing"
            ]
            
        except Exception as e:
            logger.error(f"获取插件能力失败: {e}")
            return []
    
    async def execute_cpp_plugin(self, 
                                plugin_name: str, 
                                command: str, 
                                params: Dict[str, Any]) -> Dict[str, Any]:
        """执行C++插件"""
        try:
            if not self.connected:
                await self._ensure_connected()
            
            logger.info(f"执行C++插件: {plugin_name}.{command}")
            
            # 模拟插件执行
            await asyncio.sleep(0.3)
            
            return {
                "success": True,
                "result": f"C++插件 {plugin_name} 执行 {command} 成功",
                "execution_time_ms": 300
            }
            
        except Exception as e:
            logger.error(f"C++插件执行失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _ensure_connected(self):
        """确保连接可用"""
        if not self.connected:
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                logger.info(f"尝试重新连接 gRPC... ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
                await self.connect()
            else:
                raise ConnectionError("gRPC连接失败，已达到最大重试次数")
    
    def __del__(self):
        """析构函数"""
        if self.channel and not self.channel.closed():
            # 注意：在析构函数中不能使用async/await
            pass