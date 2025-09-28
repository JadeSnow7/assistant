"""
增强型AI客户端 - 为现代化UI提供统一的后端接口
"""
import asyncio
import aiohttp
import json
import websockets
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime


class EnhancedAIClient:
    """增强型AI客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.ws_url = self.base_url.replace("http", "ws") + "/ws"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def chat(self, message: str, session_id: Optional[str] = None, 
                   **kwargs) -> Dict[str, Any]:
        """发送聊天消息"""
        data = {
            "message": message,
            "session_id": session_id,
            **kwargs
        }
        
        try:
            session = await self._get_session()
            start_time = datetime.now()
            
            async with session.post(f"{self.api_url}/chat", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # 添加响应时间
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    result["response_time"] = response_time
                    
                    return result
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def chat_stream(self, message: str, session_id: Optional[str] = None, 
                         **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天"""
        data = {
            "message": message,
            "session_id": session_id,
            **kwargs
        }
        
        try:
            session = await self._get_session()
            start_time = datetime.now()
            
            async with session.post(f"{self.api_url}/chat/stream", json=data) as response:
                if response.status == 200:
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # 去掉 'data: '
                            
                            try:
                                chunk_data = json.loads(data_str)
                                
                                # 添加响应时间到最后一个块
                                if chunk_data.get("done", False):
                                    end_time = datetime.now()
                                    response_time = (end_time - start_time).total_seconds()
                                    chunk_data["response_time"] = response_time
                                
                                yield chunk_data
                                
                            except json.JSONDecodeError:
                                continue
                else:
                    error_text = await response.text()
                    yield {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            yield {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/system/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def list_plugins(self) -> Dict[str, Any]:
        """获取插件列表"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/plugins") as response:
                if response.status == 200:
                    plugins = await response.json()
                    return {"plugins": plugins}
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件详细信息"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/plugins/{plugin_name}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def execute_plugin(self, plugin_name: str, command: str, 
                           args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行插件命令"""
        data = {
            "plugin": plugin_name,
            "command": command,
            "args": args or {}
        }
        
        try:
            session = await self._get_session()
            async with session.post(f"{self.api_url}/plugins/execute", json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def get_session_history(self, session_id: str, limit: int = 50) -> Dict[str, Any]:
        """获取会话历史"""
        try:
            session = await self._get_session()
            params = {"limit": limit}
            async with session.get(f"{self.api_url}/sessions/{session_id}/history", 
                                 params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def list_sessions(self, limit: int = 50) -> Dict[str, Any]:
        """列出会话"""
        try:
            session = await self._get_session()
            params = {"limit": limit}
            async with session.get(f"{self.api_url}/sessions", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def create_session(self, title: Optional[str] = None) -> Dict[str, Any]:
        """创建新会话"""
        data = {}
        if title:
            data["title"] = title
        
        try:
            session = await self._get_session()
            async with session.post(f"{self.api_url}/sessions", json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """删除会话"""
        try:
            session = await self._get_session()
            async with session.delete(f"{self.api_url}/sessions/{session_id}") as response:
                if response.status == 200:
                    return {"success": True}
                else:
                    error_text = await response.text()
                    return {
                        "error": f"请求失败 (HTTP {response.status}): {error_text}"
                    }
        except Exception as e:
            return {
                "error": f"网络请求失败: {str(e)}"
            }
    
    async def connect_websocket(self, session_id: Optional[str] = None):
        """连接WebSocket"""
        ws_url = f"{self.ws_url}/chat"
        if session_id:
            ws_url += f"?session_id={session_id}"
        
        try:
            return await websockets.connect(ws_url)
        except Exception as e:
            raise ConnectionError(f"WebSocket连接失败: {str(e)}")
    
    async def cleanup(self):
        """清理资源"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None


class WebSocketClient:
    """WebSocket客户端"""
    
    def __init__(self, ai_client: EnhancedAIClient):
        self.ai_client = ai_client
        self.websocket = None
        self.connected = False
    
    async def connect(self, session_id: Optional[str] = None):
        """连接WebSocket"""
        try:
            self.websocket = await self.ai_client.connect_websocket(session_id)
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            return False
    
    async def send_message(self, message: str, message_type: str = "chat"):
        """发送消息"""
        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket未连接")
        
        data = {
            "type": message_type,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(data))
    
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """接收消息"""
        if not self.connected or not self.websocket:
            return None
        
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            return None
        except Exception:
            return None
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connected = False