"""
API网关单元测试
测试HTTP API、WebSocket、认证授权、限流等功能
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import json
import time
from datetime import datetime, timedelta

from tests.test_utils import BaseTestCase, MockAPIClient, TestLevel, TestDataFactory


class TestHTTPAPI(BaseTestCase):
    """HTTP API测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.api_client = MockAPIClient()
        self.gateway = MockAPIGateway()
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_chat_endpoint(self):
        """测试聊天API端点"""
        self.start_timer()
        
        # 准备测试数据
        chat_request = TestDataFactory.create_chat_request(
            message="Hello, AI assistant!",
            max_tokens=100
        )
        
        # 设置模拟响应
        self.api_client.set_mock_response("/api/v1/chat", {
            "response": "Hello! How can I help you today?",
            "session_id": chat_request["session_id"],
            "tokens_used": 15,
            "model": "gpt-3.5-turbo",
            "finish_reason": "stop"
        })
        
        # 发送请求
        result = await self.api_client.post("/api/v1/chat", chat_request)
        
        # 验证响应
        assert result["response"] is not None
        assert result["session_id"] == chat_request["session_id"]
        assert result["tokens_used"] > 0
        assert result["finish_reason"] in ["stop", "length"]
        
        metric = self.stop_timer("chat_endpoint", TestLevel.UNIT)
        self.assert_performance(metric, 2000)  # API调用应该在2秒内完成
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_streaming_chat_endpoint(self):
        """测试流式聊天API"""
        chat_request = TestDataFactory.create_chat_request(
            message="Tell me a story",
            stream=True
        )
        
        # 模拟流式响应
        stream_chunks = [
            {"chunk": "Once", "finished": False},
            {"chunk": " upon", "finished": False},
            {"chunk": " a time", "finished": False},
            {"chunk": "...", "finished": True}
        ]
        
        self.api_client.set_mock_response("/api/v1/chat/stream", {
            "stream": True,
            "chunks": stream_chunks,
            "session_id": chat_request["session_id"]
        })
        
        result = await self.api_client.post("/api/v1/chat/stream", chat_request)
        
        assert result["stream"] is True
        assert "chunks" in result
        assert len(result["chunks"]) > 0
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_system_status_endpoint(self):
        """测试系统状态API"""
        expected_status = TestDataFactory.create_system_status()
        self.api_client.set_mock_response("/api/v1/system/status", expected_status)
        
        result = await self.api_client.get("/api/v1/system/status")
        
        assert result["status"] == "healthy"
        assert "memory" in result
        assert "cpu" in result
        assert "models" in result
        assert "plugins" in result
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_plugin_management_endpoints(self):
        """测试插件管理API"""
        # 测试插件列表
        self.api_client.set_mock_response("/api/v1/plugins", {
            "plugins": [
                {"name": "weather", "status": "loaded", "version": "1.0.0"},
                {"name": "calculator", "status": "loaded", "version": "1.1.0"}
            ]
        })
        
        result = await self.api_client.get("/api/v1/plugins")
        assert "plugins" in result
        assert len(result["plugins"]) == 2
        
        # 测试插件执行
        self.api_client.set_mock_response("/api/v1/plugins/weather/execute", {
            "result": "Current temperature: 22°C",
            "success": True,
            "execution_time": 0.15
        })
        
        result = await self.api_client.post("/api/v1/plugins/weather/execute", {
            "method": "get_current_weather",
            "args": {"location": "Tokyo"}
        })
        
        assert result["success"] is True
        assert "result" in result
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_error_handling(self):
        """测试错误处理"""
        # 测试无效请求
        self.api_client.set_mock_response("/api/v1/chat", {
            "error": "Missing required field: message",
            "status_code": 400
        })
        
        result = await self.api_client.post("/api/v1/chat", {})
        assert "error" in result
        
        # 测试服务器错误
        self.api_client.set_mock_response("/api/v1/chat", {
            "error": "Internal server error",
            "status_code": 500
        })
        
        result = await self.api_client.post("/api/v1/chat", {"message": "test"})
        assert "error" in result


class TestWebSocketAPI(BaseTestCase):
    """WebSocket API测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.websocket = MockWebSocketHandler()
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        self.start_timer()
        
        # 建立连接
        connected = await self.websocket.connect()
        assert connected is True
        assert self.websocket.is_connected() is True
        
        # 断开连接
        await self.websocket.disconnect()
        assert self.websocket.is_connected() is False
        
        metric = self.stop_timer("websocket_connection", TestLevel.UNIT)
        self.assert_performance(metric, 1000)
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_websocket_message_handling(self):
        """测试WebSocket消息处理"""
        await self.websocket.connect()
        
        # 发送聊天消息
        chat_message = {
            "type": "chat",
            "data": {
                "message": "Hello via WebSocket",
                "session_id": "ws-session-123"
            }
        }
        
        response = await self.websocket.send_message(chat_message)
        
        assert response["type"] == "chat_response"
        assert "data" in response
        assert response["data"]["session_id"] == "ws-session-123"
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_websocket_real_time_streaming(self):
        """测试WebSocket实时流式传输"""
        await self.websocket.connect()
        
        # 发送流式聊天请求
        stream_request = {
            "type": "chat_stream",
            "data": {
                "message": "Tell me a story",
                "session_id": "ws-stream-123"
            }
        }
        
        # 接收流式响应
        responses = []
        async for response in self.websocket.send_stream_message(stream_request):
            responses.append(response)
            if response.get("finished", False):
                break
                
        assert len(responses) > 1  # 应该收到多个流式片段
        assert responses[-1]["finished"] is True  # 最后一个应该标记完成
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_websocket_heartbeat(self):
        """测试WebSocket心跳机制"""
        await self.websocket.connect()
        
        # 发送心跳
        heartbeat = {"type": "ping", "timestamp": time.time()}
        response = await self.websocket.send_message(heartbeat)
        
        assert response["type"] == "pong"
        assert "timestamp" in response
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_websocket_error_handling(self):
        """测试WebSocket错误处理"""
        await self.websocket.connect()
        
        # 发送无效消息
        invalid_message = {"type": "invalid_type"}
        response = await self.websocket.send_message(invalid_message)
        
        assert response["type"] == "error"
        assert "message" in response


class TestAuthentication(BaseTestCase):
    """认证授权测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.auth = MockAuthenticator()
        
    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.security
    async def test_api_key_authentication(self):
        """测试API密钥认证"""
        # 测试有效API密钥
        valid_key = "test-api-key-123"
        result = await self.auth.validate_api_key(valid_key)
        
        assert result["valid"] is True
        assert result["user_id"] is not None
        assert result["permissions"] is not None
        
        # 测试无效API密钥
        invalid_key = "invalid-key"
        result = await self.auth.validate_api_key(invalid_key)
        
        assert result["valid"] is False
        assert "error" in result
        
    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.security
    async def test_jwt_token_authentication(self):
        """测试JWT令牌认证"""
        # 生成有效令牌
        user_info = {"user_id": "123", "username": "testuser", "role": "user"}
        token = await self.auth.generate_jwt_token(user_info)
        
        assert token is not None
        assert len(token) > 20  # JWT应该有合理长度
        
        # 验证令牌
        result = await self.auth.validate_jwt_token(token)
        
        assert result["valid"] is True
        assert result["user_id"] == "123"
        assert result["username"] == "testuser"
        
        # 测试过期令牌
        expired_token = await self.auth.generate_jwt_token(user_info, expires_in=-3600)
        result = await self.auth.validate_jwt_token(expired_token)
        
        assert result["valid"] is False
        assert "expired" in result["error"].lower()
        
    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.security
    async def test_permission_checks(self):
        """测试权限检查"""
        # 创建不同权限的用户
        admin_user = {"user_id": "admin", "role": "admin", "permissions": ["read", "write", "admin"]}
        regular_user = {"user_id": "user", "role": "user", "permissions": ["read"]}
        
        # 测试管理员权限
        result = await self.auth.check_permission(admin_user, "admin")
        assert result is True
        
        result = await self.auth.check_permission(admin_user, "write")
        assert result is True
        
        # 测试普通用户权限
        result = await self.auth.check_permission(regular_user, "read")
        assert result is True
        
        result = await self.auth.check_permission(regular_user, "admin")
        assert result is False
        
    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.security
    async def test_session_management(self):
        """测试会话管理"""
        user_info = {"user_id": "123", "username": "testuser"}
        
        # 创建会话
        session_id = await self.auth.create_session(user_info)
        assert session_id is not None
        
        # 验证会话
        session = await self.auth.get_session(session_id)
        assert session is not None
        assert session["user_id"] == "123"
        
        # 删除会话
        result = await self.auth.delete_session(session_id)
        assert result is True
        
        # 验证会话已删除
        session = await self.auth.get_session(session_id)
        assert session is None


class TestRateLimiting(BaseTestCase):
    """限流测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.rate_limiter = MockRateLimiter()
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_basic_rate_limiting(self):
        """测试基础限流"""
        client_id = "test-client-123"
        
        # 在限制内的请求应该通过
        for i in range(5):
            result = await self.rate_limiter.check_rate_limit(client_id, "chat")
            assert result["allowed"] is True
            assert result["remaining"] >= 0
            
        # 超出限制的请求应该被拒绝
        result = await self.rate_limiter.check_rate_limit(client_id, "chat")
        assert result["allowed"] is False
        assert "rate_limit_exceeded" in result
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_different_endpoints_rate_limits(self):
        """测试不同端点的限流"""
        client_id = "test-client-456"
        
        # 聊天端点限制
        chat_limit = await self.rate_limiter.get_endpoint_limit("chat")
        assert chat_limit["requests_per_minute"] == 60
        
        # 系统状态端点限制
        status_limit = await self.rate_limiter.get_endpoint_limit("system_status")
        assert status_limit["requests_per_minute"] == 10
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_rate_limit_reset(self):
        """测试限流重置"""
        client_id = "test-client-reset"
        
        # 用完配额
        for i in range(5):
            await self.rate_limiter.check_rate_limit(client_id, "chat")
            
        # 应该被限制
        result = await self.rate_limiter.check_rate_limit(client_id, "chat")
        assert result["allowed"] is False
        
        # 重置限制
        await self.rate_limiter.reset_client_limits(client_id)
        
        # 应该可以再次请求
        result = await self.rate_limiter.check_rate_limit(client_id, "chat")
        assert result["allowed"] is True
        
    @pytest.mark.unit
    @pytest.mark.api
    async def test_concurrent_rate_limiting(self):
        """测试并发限流"""
        client_id = "test-concurrent"
        
        # 并发发送请求
        tasks = [
            self.rate_limiter.check_rate_limit(client_id, "chat")
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 应该有一些请求被允许，一些被拒绝
        allowed_count = sum(1 for r in results if r["allowed"])
        rejected_count = sum(1 for r in results if not r["allowed"])
        
        assert allowed_count <= 5  # 不超过限制
        assert rejected_count >= 5  # 超出的被拒绝


# Mock classes for testing
class MockAPIGateway:
    """模拟API网关"""
    
    def __init__(self):
        self.request_count = 0
        self.endpoints = {
            "/api/v1/chat": "chat",
            "/api/v1/chat/stream": "chat_stream",
            "/api/v1/system/status": "system_status",
            "/api/v1/plugins": "plugins",
        }
        
    async def handle_request(self, endpoint: str, method: str, data: Dict = None) -> Dict[str, Any]:
        """处理HTTP请求"""
        self.request_count += 1
        
        if endpoint not in self.endpoints:
            return {"error": "Endpoint not found", "status_code": 404}
            
        endpoint_type = self.endpoints[endpoint]
        
        if endpoint_type == "chat":
            return await self._handle_chat(data)
        elif endpoint_type == "system_status":
            return await self._handle_system_status()
        # 添加更多端点处理
        
        return {"error": "Not implemented", "status_code": 501}
        
    async def _handle_chat(self, data: Dict) -> Dict[str, Any]:
        """处理聊天请求"""
        if not data or "message" not in data:
            return {"error": "Missing required field: message", "status_code": 400}
            
        return {
            "response": f"Mock response to: {data['message']}",
            "session_id": data.get("session_id"),
            "tokens_used": len(data["message"].split()) * 2,
            "model": "mock-model",
            "finish_reason": "stop"
        }
        
    async def _handle_system_status(self) -> Dict[str, Any]:
        """处理系统状态请求"""
        return TestDataFactory.create_system_status()


class MockWebSocketHandler:
    """模拟WebSocket处理器"""
    
    def __init__(self):
        self.connected = False
        self.message_count = 0
        
    async def connect(self) -> bool:
        """连接WebSocket"""
        self.connected = True
        return True
        
    async def disconnect(self):
        """断开WebSocket"""
        self.connected = False
        
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected
        
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息"""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")
            
        self.message_count += 1
        
        message_type = message.get("type")
        
        if message_type == "chat":
            return {
                "type": "chat_response",
                "data": {
                    "response": f"WebSocket response to: {message['data']['message']}",
                    "session_id": message["data"]["session_id"],
                    "timestamp": time.time()
                }
            }
        elif message_type == "ping":
            return {
                "type": "pong",
                "timestamp": time.time()
            }
        else:
            return {
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }
            
    async def send_stream_message(self, message: Dict[str, Any]):
        """发送流式消息"""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")
            
        # 模拟流式响应
        chunks = ["Hello", " there!", " How", " can", " I", " help", " you", " today?"]
        
        for i, chunk in enumerate(chunks):
            yield {
                "type": "chat_stream",
                "data": {
                    "chunk": chunk,
                    "finished": i == len(chunks) - 1,
                    "session_id": message["data"]["session_id"]
                }
            }
            await asyncio.sleep(0.1)  # 模拟延迟


class MockAuthenticator:
    """模拟认证器"""
    
    def __init__(self):
        self.valid_api_keys = {
            "test-api-key-123": {"user_id": "123", "permissions": ["read", "write"]},
            "admin-key-456": {"user_id": "admin", "permissions": ["read", "write", "admin"]}
        }
        self.sessions = {}
        
    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """验证API密钥"""
        if api_key in self.valid_api_keys:
            user_info = self.valid_api_keys[api_key]
            return {
                "valid": True,
                "user_id": user_info["user_id"],
                "permissions": user_info["permissions"]
            }
        else:
            return {
                "valid": False,
                "error": "Invalid API key"
            }
            
    async def generate_jwt_token(self, user_info: Dict[str, Any], expires_in: int = 3600) -> str:
        """生成JWT令牌"""
        # 简化的JWT生成
        import base64
        import json
        
        header = {"typ": "JWT", "alg": "HS256"}
        payload = {
            **user_info,
            "exp": time.time() + expires_in,
            "iat": time.time()
        }
        
        header_encoded = base64.b64encode(json.dumps(header).encode()).decode()
        payload_encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        signature = "mock-signature"
        
        return f"{header_encoded}.{payload_encoded}.{signature}"
        
    async def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """验证JWT令牌"""
        try:
            import base64
            import json
            
            parts = token.split(".")
            if len(parts) != 3:
                return {"valid": False, "error": "Invalid token format"}
                
            payload_data = base64.b64decode(parts[1]).decode()
            payload = json.loads(payload_data)
            
            # 检查过期时间
            if payload.get("exp", 0) < time.time():
                return {"valid": False, "error": "Token expired"}
                
            return {
                "valid": True,
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "role": payload.get("role")
            }
        except Exception as e:
            return {"valid": False, "error": f"Token validation error: {str(e)}"}
            
    async def check_permission(self, user: Dict[str, Any], required_permission: str) -> bool:
        """检查权限"""
        user_permissions = user.get("permissions", [])
        return required_permission in user_permissions
        
    async def create_session(self, user_info: Dict[str, Any]) -> str:
        """创建会话"""
        session_id = f"session-{int(time.time())}-{user_info['user_id']}"
        self.sessions[session_id] = {
            **user_info,
            "created_at": time.time(),
            "last_accessed": time.time()
        }
        return session_id
        
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """获取会话"""
        return self.sessions.get(session_id)
        
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


class MockRateLimiter:
    """模拟限流器"""
    
    def __init__(self):
        self.client_requests = {}
        self.endpoint_limits = {
            "chat": {"requests_per_minute": 60, "window_size": 60},
            "system_status": {"requests_per_minute": 10, "window_size": 60},
            "plugins": {"requests_per_minute": 30, "window_size": 60}
        }
        # 简化的限流实现，实际项目中应使用Redis等
        self.simple_limits = {}
        
    async def check_rate_limit(self, client_id: str, endpoint: str) -> Dict[str, Any]:
        """检查限流"""
        current_time = time.time()
        key = f"{client_id}:{endpoint}"
        
        if key not in self.simple_limits:
            self.simple_limits[key] = {"count": 0, "reset_time": current_time + 60}
            
        limit_info = self.simple_limits[key]
        
        # 检查是否需要重置
        if current_time > limit_info["reset_time"]:
            limit_info["count"] = 0
            limit_info["reset_time"] = current_time + 60
            
        # 检查限制
        endpoint_config = self.endpoint_limits.get(endpoint, {"requests_per_minute": 60})
        max_requests = endpoint_config["requests_per_minute"]
        
        if endpoint == "chat":
            max_requests = 5  # 为了测试方便，设置较低的限制
            
        if limit_info["count"] >= max_requests:
            return {
                "allowed": False,
                "rate_limit_exceeded": True,
                "reset_time": limit_info["reset_time"],
                "remaining": 0
            }
        else:
            limit_info["count"] += 1
            return {
                "allowed": True,
                "remaining": max_requests - limit_info["count"],
                "reset_time": limit_info["reset_time"]
            }
            
    async def get_endpoint_limit(self, endpoint: str) -> Dict[str, Any]:
        """获取端点限制"""
        return self.endpoint_limits.get(endpoint, {"requests_per_minute": 60})
        
    async def reset_client_limits(self, client_id: str):
        """重置客户端限制"""
        keys_to_remove = [key for key in self.simple_limits.keys() if key.startswith(client_id)]
        for key in keys_to_remove:
            del self.simple_limits[key]