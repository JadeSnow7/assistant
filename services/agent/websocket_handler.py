"""
WebSocket处理器
"""
import asyncio
import json
import logging
from typing import Dict, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid

from interfaces.api.schemas import WebSocketMessage, ConnectionInfo
from services.agent.orchestrator import AgentOrchestrator


logger = logging.getLogger(__name__)

websocket_router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 连接信息
        self.connection_info: Dict[str, ConnectionInfo] = {}
        # 会话到连接的映射
        self.session_connections: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """接受新连接"""
        await websocket.accept()
        
        if not connection_id:
            connection_id = str(uuid.uuid4())
        
        self.active_connections[connection_id] = websocket
        
        # 创建连接信息
        client_info = websocket.headers
        self.connection_info[connection_id] = ConnectionInfo(
            connection_id=connection_id,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
            user_agent=client_info.get("user-agent"),
            ip_address=client_info.get("x-forwarded-for") or client_info.get("x-real-ip")
        )
        
        logger.info(f"WebSocket连接建立: {connection_id}")
        return connection_id
    
    def disconnect(self, connection_id: str):
        """断开连接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if connection_id in self.connection_info:
            # 从会话映射中移除
            conn_info = self.connection_info[connection_id]
            if conn_info.session_id:
                session_conns = self.session_connections.get(conn_info.session_id, set())
                session_conns.discard(connection_id)
                if not session_conns:
                    del self.session_connections[conn_info.session_id]
            
            del self.connection_info[connection_id]
        
        logger.info(f"WebSocket连接断开: {connection_id}")
    
    def bind_session(self, connection_id: str, session_id: str):
        """绑定会话ID"""
        if connection_id in self.connection_info:
            self.connection_info[connection_id].session_id = session_id
            
            # 更新会话映射
            if session_id not in self.session_connections:
                self.session_connections[session_id] = set()
            self.session_connections[session_id].add(connection_id)
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """发送个人消息"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
                
                # 更新活动时间
                if connection_id in self.connection_info:
                    self.connection_info[connection_id].last_activity = datetime.now()
                    
            except Exception as e:
                logger.error(f"发送消息失败 {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_session_message(self, message: dict, session_id: str):
        """发送会话消息（给同一会话的所有连接）"""
        if session_id in self.session_connections:
            connection_ids = list(self.session_connections[session_id])
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast(self, message: dict):
        """广播消息"""
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    def get_connection_count(self) -> int:
        """获取连接数"""
        return len(self.active_connections)
    
    def get_session_connections(self, session_id: str) -> Set[str]:
        """获取会话的所有连接"""
        return self.session_connections.get(session_id, set())


# 全局连接管理器
connection_manager = ConnectionManager()


@websocket_router.websocket("/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket聊天端点"""
    connection_id = await connection_manager.connect(websocket)
    
    try:
        # 发送欢迎消息
        welcome_msg = {
            "type": "system",
            "data": {
                "message": "WebSocket连接建立成功",
                "connection_id": connection_id
            },
            "timestamp": datetime.now().isoformat()
        }
        await connection_manager.send_personal_message(welcome_msg, connection_id)
        
        # 消息处理循环
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # 处理消息
                await handle_websocket_message(message_data, connection_id)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket客户端主动断开: {connection_id}")
                break
            except json.JSONDecodeError:
                # 发送错误消息
                error_msg = {
                    "type": "error",
                    "data": {"message": "消息格式错误，请发送有效的JSON"},
                    "timestamp": datetime.now().isoformat()
                }
                await connection_manager.send_personal_message(error_msg, connection_id)
            except Exception as e:
                logger.error(f"WebSocket消息处理错误: {e}")
                error_msg = {
                    "type": "error", 
                    "data": {"message": f"消息处理失败: {str(e)}"},
                    "timestamp": datetime.now().isoformat()
                }
                await connection_manager.send_personal_message(error_msg, connection_id)
                
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        connection_manager.disconnect(connection_id)


async def handle_websocket_message(message_data: dict, connection_id: str):
    """处理WebSocket消息"""
    message_type = message_data.get("type", "")
    data = message_data.get("data", {})
    
    if message_type == "chat":
        await handle_chat_message(data, connection_id)
    elif message_type == "ping":
        await handle_ping_message(connection_id)
    elif message_type == "session_bind":
        await handle_session_bind(data, connection_id)
    else:
        # 未知消息类型
        error_msg = {
            "type": "error",
            "data": {"message": f"未知消息类型: {message_type}"},
            "timestamp": datetime.now().isoformat()
        }
        await connection_manager.send_personal_message(error_msg, connection_id)


async def handle_chat_message(data: dict, connection_id: str):
    """处理聊天消息"""
    try:
        message = data.get("message", "")
        session_id = data.get("session_id")
        
        if not message:
            error_msg = {
                "type": "error",
                "data": {"message": "消息内容不能为空"},
                "timestamp": datetime.now().isoformat()
            }
            await connection_manager.send_personal_message(error_msg, connection_id)
            return
        
        # 绑定会话ID
        if session_id:
            connection_manager.bind_session(connection_id, session_id)
        
        # 发送用户消息确认
        user_msg = {
            "type": "user_message",
            "data": {
                "message": message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        }
        await connection_manager.send_personal_message(user_msg, connection_id)
        
        # 发送AI思考状态
        thinking_msg = {
            "type": "ai_thinking",
            "data": {"message": "AI正在思考中..."},
            "timestamp": datetime.now().isoformat()
        }
        await connection_manager.send_personal_message(thinking_msg, connection_id)
        
        # 这里应该调用Agent调度器处理消息
        # 为了演示，我们发送一个模拟响应
        await asyncio.sleep(1)  # 模拟处理时间
        
        ai_response = {
            "type": "ai_response",
            "data": {
                "content": f"这是对'{message}'的WebSocket模拟回复",
                "session_id": session_id,
                "model_used": "local_small",
                "reasoning": "WebSocket模拟回复",
                "timestamp": datetime.now().isoformat()
            }
        }
        await connection_manager.send_personal_message(ai_response, connection_id)
        
    except Exception as e:
        logger.error(f"处理聊天消息失败: {e}")
        error_msg = {
            "type": "error",
            "data": {"message": "消息处理失败"},
            "timestamp": datetime.now().isoformat()
        }
        await connection_manager.send_personal_message(error_msg, connection_id)


async def handle_ping_message(connection_id: str):
    """处理ping消息"""
    pong_msg = {
        "type": "pong",
        "data": {"timestamp": datetime.now().isoformat()},
        "timestamp": datetime.now().isoformat()
    }
    await connection_manager.send_personal_message(pong_msg, connection_id)


async def handle_session_bind(data: dict, connection_id: str):
    """处理会话绑定"""
    session_id = data.get("session_id")
    
    if session_id:
        connection_manager.bind_session(connection_id, session_id)
        
        success_msg = {
            "type": "session_bound",
            "data": {
                "session_id": session_id,
                "message": "会话绑定成功"
            },
            "timestamp": datetime.now().isoformat()
        }
        await connection_manager.send_personal_message(success_msg, connection_id)
    else:
        error_msg = {
            "type": "error",
            "data": {"message": "会话ID不能为空"},
            "timestamp": datetime.now().isoformat()
        }
        await connection_manager.send_personal_message(error_msg, connection_id)


@websocket_router.websocket("/system")
async def websocket_system_endpoint(websocket: WebSocket):
    """系统信息WebSocket端点"""
    connection_id = await connection_manager.connect(websocket)
    
    try:
        while True:
            # 每5秒发送一次系统状态
            await asyncio.sleep(5)
            
            system_status = {
                "type": "system_status",
                "data": {
                    "active_connections": connection_manager.get_connection_count(),
                    "timestamp": datetime.now().isoformat(),
                    # 这里可以添加更多系统信息
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await connection_manager.send_personal_message(system_status, connection_id)
            
    except WebSocketDisconnect:
        logger.info(f"系统监控WebSocket断开: {connection_id}")
    except Exception as e:
        logger.error(f"系统监控WebSocket错误: {e}")
    finally:
        connection_manager.disconnect(connection_id)