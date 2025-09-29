"""
API集成测试
测试完整的API工作流程和跨模块交互
"""
import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any
import time

from tests.test_utils import BaseTestCase, TestLevel, TestDataFactory


@pytest.mark.integration
@pytest.mark.api
class TestAPIWorkflow(BaseTestCase):
    """API工作流集成测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.base_url = "http://localhost:8000"
        self.session_id = f"integration-test-{int(time.time())}"
        
    @pytest.mark.asyncio
    async def test_complete_chat_workflow(self):
        """测试完整聊天工作流"""
        self.start_timer()
        
        async with aiohttp.ClientSession() as session:
            # 1. 健康检查
            async with session.get(f"{self.base_url}/health") as resp:
                assert resp.status == 200
                health_data = await resp.json()
                assert health_data["status"] == "healthy"
            
            # 2. 发送聊天请求
            chat_data = TestDataFactory.create_chat_request(
                message="Hello, this is an integration test",
                session_id=self.session_id
            )
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=chat_data) as resp:
                assert resp.status == 200
                chat_response = await resp.json()
                
                assert "response" in chat_response
                assert chat_response["session_id"] == self.session_id
                assert chat_response["tokens_used"] > 0
            
            # 3. 检查会话历史
            async with session.get(f"{self.base_url}/api/v1/sessions/{self.session_id}/history") as resp:
                assert resp.status == 200
                history = await resp.json()
                
                assert len(history["messages"]) >= 2  # 用户消息 + AI响应
                assert history["session_id"] == self.session_id
            
            # 4. 系统状态检查
            async with session.get(f"{self.base_url}/api/v1/system/status") as resp:
                assert resp.status == 200
                status = await resp.json()
                
                assert status["status"] == "healthy"
                assert "memory" in status
                assert "cpu" in status
        
        metric = self.stop_timer("complete_chat_workflow", TestLevel.INTEGRATION)
        self.assert_performance(metric, 5000)  # 完整工作流应在5秒内完成
    
    @pytest.mark.asyncio
    async def test_streaming_chat_integration(self):
        """测试流式聊天集成"""
        async with aiohttp.ClientSession() as session:
            chat_data = TestDataFactory.create_chat_request(
                message="Tell me a story about AI",
                session_id=self.session_id,
                stream=True
            )
            
            self.start_timer()
            
            async with session.post(f"{self.base_url}/api/v1/chat/stream", json=chat_data) as resp:
                assert resp.status == 200
                assert resp.headers.get("content-type") == "text/event-stream"
                
                chunks_received = 0
                full_content = ""
                
                async for line in resp.content:
                    if line:
                        line_text = line.decode('utf-8').strip()
                        if line_text.startswith("data: "):
                            chunk_data = json.loads(line_text[6:])
                            
                            if "content" in chunk_data:
                                full_content += chunk_data["content"]
                                chunks_received += 1
                            
                            if chunk_data.get("finished", False):
                                break
                
                assert chunks_received > 0
                assert len(full_content) > 0
            
            metric = self.stop_timer("streaming_chat_integration", TestLevel.INTEGRATION)
            self.assert_performance(metric, 10000)  # 流式响应可能需要更长时间
    
    @pytest.mark.asyncio
    async def test_plugin_integration_workflow(self):
        """测试插件集成工作流"""
        async with aiohttp.ClientSession() as session:
            # 1. 获取插件列表
            async with session.get(f"{self.base_url}/api/v1/plugins") as resp:
                assert resp.status == 200
                plugins = await resp.json()
                
                assert "plugins" in plugins
                assert len(plugins["plugins"]) > 0
            
            # 2. 加载特定插件
            weather_plugin = {
                "name": "weather",
                "config": {"api_key": "test-key"}
            }
            
            async with session.post(f"{self.base_url}/api/v1/plugins/load", json=weather_plugin) as resp:
                assert resp.status == 200
                load_result = await resp.json()
                assert load_result["success"] is True
            
            # 3. 执行插件功能
            plugin_exec = {
                "method": "get_current_weather",
                "args": {"location": "Tokyo"}
            }
            
            async with session.post(f"{self.base_url}/api/v1/plugins/weather/execute", json=plugin_exec) as resp:
                assert resp.status == 200
                exec_result = await resp.json()
                
                assert exec_result["success"] is True
                assert "result" in exec_result
            
            # 4. 在聊天中使用插件
            chat_with_plugin = TestDataFactory.create_chat_request(
                message="What's the weather like in Tokyo?",
                session_id=self.session_id
            )
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=chat_with_plugin) as resp:
                assert resp.status == 200
                chat_response = await resp.json()
                
                # 响应应该包含天气信息
                assert "weather" in chat_response["response"].lower()
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """测试错误恢复集成"""
        async with aiohttp.ClientSession() as session:
            # 1. 发送无效请求
            invalid_data = {"invalid": "request"}
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=invalid_data) as resp:
                assert resp.status == 400
                error_response = await resp.json()
                assert "error" in error_response
            
            # 2. 系统应该仍然正常运行
            async with session.get(f"{self.base_url}/health") as resp:
                assert resp.status == 200
                health_data = await resp.json()
                assert health_data["status"] == "healthy"
            
            # 3. 正常请求应该仍然工作
            valid_data = TestDataFactory.create_chat_request("Test after error")
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=valid_data) as resp:
                assert resp.status == 200
                response_data = await resp.json()
                assert "response" in response_data


@pytest.mark.integration
@pytest.mark.api
class TestAPIPerformanceIntegration(BaseTestCase):
    """API性能集成测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.base_url = "http://localhost:8000"
        
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求处理"""
        self.start_timer()
        
        async with aiohttp.ClientSession() as session:
            # 创建多个并发聊天请求
            tasks = []
            for i in range(10):
                chat_data = TestDataFactory.create_chat_request(
                    message=f"Concurrent request {i}",
                    session_id=f"concurrent-{i}"
                )
                
                task = session.post(f"{self.base_url}/api/v1/chat", json=chat_data)
                tasks.append(task)
            
            # 等待所有请求完成
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 验证结果
            successful_responses = 0
            for response in responses:
                if isinstance(response, aiohttp.ClientResponse):
                    if response.status == 200:
                        successful_responses += 1
                    response.close()
            
            assert successful_responses >= 8  # 至少80%的请求成功
        
        metric = self.stop_timer("concurrent_requests", TestLevel.INTEGRATION)
        self.assert_performance(metric, 15000)  # 并发请求应在15秒内完成
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """测试限流集成"""
        async with aiohttp.ClientSession() as session:
            # 快速发送多个请求以触发限流
            responses = []
            for i in range(20):  # 发送超过限制的请求数
                chat_data = TestDataFactory.create_chat_request(
                    message=f"Rate limit test {i}",
                    session_id="rate-limit-test"
                )
                
                try:
                    async with session.post(f"{self.base_url}/api/v1/chat", json=chat_data) as resp:
                        responses.append(resp.status)
                except Exception as e:
                    responses.append(429)  # Rate limited
            
            # 应该有一些请求被限流（返回429状态码）
            rate_limited_count = responses.count(429)
            successful_count = responses.count(200)
            
            assert rate_limited_count > 0  # 应该有请求被限流
            assert successful_count > 0   # 也应该有请求成功
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        async with aiohttp.ClientSession() as session:
            # 获取初始内存使用
            async with session.get(f"{self.base_url}/api/v1/system/status") as resp:
                initial_status = await resp.json()
                initial_memory = initial_status["memory"]["usage_percent"]
            
            # 发送大量请求
            for i in range(50):
                chat_data = TestDataFactory.create_chat_request(
                    message=f"Memory test request {i} with longer content to test memory usage patterns",
                    session_id=f"memory-test-{i % 5}"  # 复用会话
                )
                
                async with session.post(f"{self.base_url}/api/v1/chat", json=chat_data) as resp:
                    if resp.status == 200:
                        await resp.json()  # 读取响应
            
            # 检查最终内存使用
            async with session.get(f"{self.base_url}/api/v1/system/status") as resp:
                final_status = await resp.json()
                final_memory = final_status["memory"]["usage_percent"]
            
            # 内存增长应该在合理范围内
            memory_increase = final_memory - initial_memory
            assert memory_increase < 20  # 内存增长不应超过20%


@pytest.mark.integration
@pytest.mark.api 
class TestCrossModuleIntegration(BaseTestCase):
    """跨模块集成测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.base_url = "http://localhost:8000"
        
    @pytest.mark.asyncio
    async def test_ai_model_plugin_integration(self):
        """测试AI模型与插件集成"""
        async with aiohttp.ClientSession() as session:
            # 1. 确保插件已加载
            async with session.get(f"{self.base_url}/api/v1/plugins") as resp:
                plugins = await resp.json()
                weather_loaded = any(p["name"] == "weather" for p in plugins["plugins"])
                
                if not weather_loaded:
                    # 加载天气插件
                    load_data = {"name": "weather", "config": {"api_key": "test"}}
                    async with session.post(f"{self.base_url}/api/v1/plugins/load", json=load_data) as resp:
                        assert resp.status == 200
            
            # 2. 发送需要插件协助的聊天请求
            chat_data = TestDataFactory.create_chat_request(
                message="Can you check the weather in Tokyo and give me some travel advice?",
                session_id="ai-plugin-integration"
            )
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=chat_data) as resp:
                assert resp.status == 200
                response = await resp.json()
                
                # AI应该能够调用天气插件并提供综合建议
                assert "weather" in response["response"].lower()
                assert len(response["response"]) > 100  # 应该是详细的回复
                
                # 检查是否记录了插件调用
                if "plugin_calls" in response:
                    assert len(response["plugin_calls"]) > 0
                    assert any("weather" in call.get("plugin", "") for call in response["plugin_calls"])
    
    @pytest.mark.asyncio
    async def test_memory_persistence_integration(self):
        """测试记忆持久化集成"""
        session_id = "memory-persistence-test"
        
        async with aiohttp.ClientSession() as session:
            # 1. 第一轮对话
            first_chat = TestDataFactory.create_chat_request(
                message="My name is Alice and I love programming",
                session_id=session_id
            )
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=first_chat) as resp:
                assert resp.status == 200
                first_response = await resp.json()
                assert "Alice" in first_response["response"]
            
            # 2. 第二轮对话 - 测试上下文记忆
            second_chat = TestDataFactory.create_chat_request(
                message="What did I just tell you about my interests?",
                session_id=session_id
            )
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=second_chat) as resp:
                assert resp.status == 200
                second_response = await resp.json()
                
                # AI应该记住之前的对话内容
                response_text = second_response["response"].lower()
                assert "programming" in response_text or "alice" in response_text
            
            # 3. 获取会话历史验证
            async with session.get(f"{self.base_url}/api/v1/sessions/{session_id}/history") as resp:
                assert resp.status == 200
                history = await resp.json()
                
                assert len(history["messages"]) >= 4  # 至少2轮对话（用户+AI各2条）
                assert any("Alice" in msg["content"] for msg in history["messages"])
                assert any("programming" in msg["content"] for msg in history["messages"])
    
    @pytest.mark.asyncio
    async def test_routing_fallback_integration(self):
        """测试路由降级集成"""
        async with aiohttp.ClientSession() as session:
            # 1. 发送复杂任务（应路由到云端）
            complex_chat = TestDataFactory.create_chat_request(
                message="Write a comprehensive analysis of quantum computing's impact on modern cryptography, including technical details about Shor's algorithm and post-quantum cryptographic methods.",
                session_id="routing-test-complex"
            )
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=complex_chat) as resp:
                assert resp.status == 200
                complex_response = await resp.json()
                
                # 复杂响应应该更详细
                assert len(complex_response["response"]) > 200
                
                # 检查路由信息
                if "routing_info" in complex_response:
                    assert complex_response["routing_info"]["complexity"] > 0.5
            
            # 2. 发送简单任务（应路由到本地）
            simple_chat = TestDataFactory.create_chat_request(
                message="What is 2+2?",
                session_id="routing-test-simple"
            )
            
            async with session.post(f"{self.base_url}/api/v1/chat", json=simple_chat) as resp:
                assert resp.status == 200
                simple_response = await resp.json()
                
                assert "4" in simple_response["response"]
                
                # 简单任务的响应时间应该更快
                if "response_time_ms" in simple_response:
                    assert simple_response["response_time_ms"] < 1000
    
    @pytest.mark.asyncio
    async def test_system_monitoring_integration(self):
        """测试系统监控集成"""
        async with aiohttp.ClientSession() as session:
            # 1. 获取初始系统状态
            async with session.get(f"{self.base_url}/api/v1/system/status") as resp:
                assert resp.status == 200
                initial_status = await resp.json()
                
                assert "cpu" in initial_status
                assert "memory" in initial_status
                assert "connections" in initial_status
            
            # 2. 发送一些负载
            for i in range(10):
                chat_data = TestDataFactory.create_chat_request(
                    message=f"Load test message {i}",
                    session_id=f"load-test-{i}"
                )
                
                async with session.post(f"{self.base_url}/api/v1/chat", json=chat_data) as resp:
                    if resp.status == 200:
                        await resp.json()
            
            # 3. 检查系统状态变化
            async with session.get(f"{self.base_url}/api/v1/system/status") as resp:
                assert resp.status == 200
                final_status = await resp.json()
                
                # 连接数或处理计数应该有变化
                assert final_status["connections"]["total"] >= initial_status["connections"]["total"]
            
            # 4. 检查系统指标
            async with session.get(f"{self.base_url}/api/v1/system/metrics") as resp:
                assert resp.status == 200
                metrics = await resp.json()
                
                # 应该有请求统计
                assert "requests_total" in metrics
                assert metrics["requests_total"] > 0
                
                # 应该有响应时间统计
                assert "response_time_avg" in metrics
                assert metrics["response_time_avg"] > 0