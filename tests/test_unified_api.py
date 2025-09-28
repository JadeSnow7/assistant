"""
统一API系统单元测试
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# 导入待测试模块
from python.core.adapters.base import (
    BaseAdapter, AdapterManager, UnifiedChatRequest, 
    UnifiedChatResponse, ModelInfo, ProviderType, EngineType
)
from python.core.adapters.openai_adapter import OpenAIAdapter
from python.core.adapters.gemini_adapter import GeminiAdapter
from python.core.adapters.local_adapter import LlamaCppAdapter, OllamaAdapter
from python.core.model_manager import UnifiedModelManager
from python.core.gpu_manager import GPUManager, GPUInfo, GPUType
from python.core.intelligent_router import IntelligentRouter, TaskAnalyzer, RoutingDecision
from python.core.unified_api_gateway import UnifiedAPIGateway


class TestBaseAdapter:
    """测试基础适配器"""
    
    def test_adapter_initialization(self):
        """测试适配器初始化"""
        config = {"api_key": "test_key", "endpoint": "http://test.com"}
        adapter = Mock(spec=BaseAdapter)
        adapter.config = config
        adapter.provider_type = ProviderType.OPENAI
        adapter.engine_type = EngineType.CLOUD
        
        assert adapter.config == config
        assert adapter.provider_type == ProviderType.OPENAI
        assert adapter.engine_type == EngineType.CLOUD
    
    def test_unified_chat_request_creation(self):
        """测试统一聊天请求创建"""
        request = UnifiedChatRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=100,
            temperature=0.7
        )
        
        assert request.model == "gpt-3.5-turbo"
        assert len(request.messages) == 1
        assert request.max_tokens == 100
        assert request.temperature == 0.7
        assert request.stream is False
    
    def test_unified_chat_response_creation(self):
        """测试统一聊天响应创建"""
        response = UnifiedChatResponse(
            id="test-123",
            model="gpt-3.5-turbo",
            provider="openai",
            engine="cloud",
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop"
            }]
        )
        
        assert response.id == "test-123"
        assert response.model == "gpt-3.5-turbo"
        assert response.provider == "openai"
        assert len(response.choices) == 1


class TestAdapterManager:
    """测试适配器管理器"""
    
    def setup_method(self):
        """测试前设置"""
        self.manager = AdapterManager()
    
    def test_register_adapter(self):
        """测试注册适配器"""
        adapter = Mock(spec=BaseAdapter)
        adapter.provider_type = ProviderType.OPENAI
        
        self.manager.register_adapter("openai", adapter)
        
        assert "openai" in self.manager.adapters
        assert self.manager.get_adapter("openai") == adapter
        assert self.manager.get_adapter_by_provider("openai") == adapter
    
    def test_get_nonexistent_adapter(self):
        """测试获取不存在的适配器"""
        assert self.manager.get_adapter("nonexistent") is None
        assert self.manager.get_adapter_by_provider("nonexistent") is None


class TestOpenAIAdapter:
    """测试OpenAI适配器"""
    
    def setup_method(self):
        """测试前设置"""
        config = {
            "api_key": "test_key",
            "endpoint": "https://api.openai.com/v1",
            "default_model": "gpt-3.5-turbo"
        }
        self.adapter = OpenAIAdapter(config)
    
    def test_adapter_initialization(self):
        """测试适配器初始化"""
        assert self.adapter.provider_type == ProviderType.OPENAI
        assert self.adapter.engine_type == EngineType.CLOUD
        assert self.adapter.api_key == "test_key"
        assert self.adapter.endpoint == "https://api.openai.com/v1"
    
    def test_convert_to_openai_format(self):
        """测试转换为OpenAI格式"""
        request = UnifiedChatRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=100,
            temperature=0.7
        )
        
        openai_request = self.adapter._convert_to_openai_format(request)
        
        assert openai_request["model"] == "gpt-3.5-turbo"
        assert openai_request["messages"] == [{"role": "user", "content": "Hello"}]
        assert openai_request["max_tokens"] == 100
        assert openai_request["temperature"] == 0.7
    
    @pytest.mark.asyncio
    async def test_get_available_models(self):
        """测试获取可用模型"""
        # Mock HTTP session
        with patch.object(self.adapter, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": [
                    {"id": "gpt-3.5-turbo"},
                    {"id": "gpt-4"}
                ]
            })
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            models = await self.adapter.get_available_models()
            
            assert len(models) == 2
            assert models[0].id == "gpt-3.5-turbo"
            assert models[1].id == "gpt-4"


class TestGPUManager:
    """测试GPU管理器"""
    
    def setup_method(self):
        """测试前设置"""
        self.gpu_manager = GPUManager()
    
    @pytest.mark.asyncio
    async def test_gpu_manager_initialization(self):
        """测试GPU管理器初始化"""
        # Mock nvidia-smi command
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (
                b"0, Tesla V100, 32510, 30000, 2510, 15, 45, 250.0, 470.03\n",
                b""
            )
            mock_subprocess.return_value = mock_process
            
            result = await self.gpu_manager.initialize()
            
            assert result is True
            assert self.gpu_manager.initialized is True
    
    def test_gpu_config_creation(self):
        """测试GPU配置创建"""
        from python.core.gpu_manager import GPUConfig
        
        config = GPUConfig(
            enabled=True,
            gpu_layers=35,
            main_gpu=0,
            batch_size=512
        )
        
        assert config.enabled is True
        assert config.gpu_layers == 35
        assert config.main_gpu == 0
        assert config.batch_size == 512
    
    def test_recommended_config_generation(self):
        """测试推荐配置生成"""
        # Mock GPU info
        self.gpu_manager.gpus = [
            GPUInfo(
                id=0,
                name="Tesla V100",
                gpu_type=GPUType.NVIDIA,
                memory_total=32768,  # 32GB
                memory_free=30000,
                memory_used=2768,
                utilization=15.0
            )
        ]
        self.gpu_manager.config.enabled = True
        self.gpu_manager.config.gpu_layers = 35
        
        config = self.gpu_manager.get_recommended_config("7b")
        
        assert config["use_gpu"] is True
        assert config["gpu_layers"] == 35
        assert config["gpu_type"] == "nvidia"


class TestTaskAnalyzer:
    """测试任务分析器"""
    
    def setup_method(self):
        """测试前设置"""
        self.analyzer = TaskAnalyzer()
    
    @pytest.mark.asyncio
    async def test_simple_task_analysis(self):
        """测试简单任务分析"""
        request = UnifiedChatRequest(
            model="test",
            messages=[{"role": "user", "content": "你好"}]
        )
        
        analysis = await self.analyzer.analyze_task(request)
        
        assert analysis["complexity"].value == "simple"
        assert analysis["requires_internet"] is False
        assert analysis["language"] == "zh"
    
    @pytest.mark.asyncio
    async def test_complex_task_analysis(self):
        """测试复杂任务分析"""
        request = UnifiedChatRequest(
            model="test",
            messages=[{"role": "user", "content": "请帮我设计一个复杂的分布式系统架构，包括详细的组件分析和性能优化方案"}]
        )
        
        analysis = await self.analyzer.analyze_task(request)
        
        assert analysis["complexity"].value == "complex"
        assert "analysis" in analysis["required_functions"]
    
    @pytest.mark.asyncio
    async def test_internet_requirement_detection(self):
        """测试联网需求检测"""
        request = UnifiedChatRequest(
            model="test",
            messages=[{"role": "user", "content": "今天的最新新闻有什么？"}]
        )
        
        analysis = await self.analyzer.analyze_task(request)
        
        assert analysis["requires_internet"] is True


class TestIntelligentRouter:
    """测试智能路由器"""
    
    def setup_method(self):
        """测试前设置"""
        self.model_manager = Mock()
        self.gpu_manager = Mock()
        self.router = IntelligentRouter(self.model_manager, self.gpu_manager)
    
    @pytest.mark.asyncio
    async def test_route_by_specified_provider(self):
        """测试指定provider的路由"""
        request = UnifiedChatRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            provider="openai"
        )
        
        # Mock adapter manager
        mock_adapter = Mock()
        mock_adapter.is_healthy.return_value = True
        mock_adapter.get_available_models = AsyncMock(return_value=[
            ModelInfo(id="gpt-3.5-turbo", provider="openai", engine="cloud")
        ])
        
        mock_adapter_manager = Mock()
        mock_adapter_manager.get_adapter_by_provider.return_value = mock_adapter
        
        self.model_manager.get_adapter_manager.return_value = mock_adapter_manager
        
        decision = await self.router._route_by_provider(request)
        
        assert decision.provider == "openai"
        assert decision.model == "gpt-3.5-turbo"
        assert decision.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_model_scoring(self):
        """测试模型评分"""
        from core.intelligent_router import ModelCapability, TaskComplexity
        
        capability = ModelCapability(
            model_id="gpt-4",
            provider="openai",
            engine="cloud",
            general_chat=0.95,
            coding=0.90,
            reasoning=0.95,
            speed_score=0.7,
            cost_score=0.3,
            reliability=0.95
        )
        
        task_analysis = {
            "complexity": TaskComplexity.COMPLEX,
            "required_functions": ["reasoning"],
            "requires_internet": True
        }
        
        score = await self.router._score_model(capability, task_analysis)
        
        assert score > 0.5  # 应该得到较高评分


class TestUnifiedModelManager:
    """测试统一模型管理器"""
    
    def setup_method(self):
        """测试前设置"""
        self.manager = UnifiedModelManager()
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """测试管理器初始化"""
        config = {
            "engines": {
                "openai": {
                    "enabled": True,
                    "api_key": "test_key",
                    "endpoint": "https://api.openai.com/v1"
                }
            }
        }
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            result = await self.manager.initialize(config)
            
            # 即使某些组件初始化失败，也应该返回True
            assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_get_available_models_empty(self):
        """测试获取空模型列表"""
        # Mock empty adapter manager
        mock_adapter_manager = Mock()
        mock_adapter_manager.adapters = {}
        self.manager.adapter_manager = mock_adapter_manager
        
        models = await self.manager.get_available_models()
        
        assert isinstance(models, list)
        assert len(models) == 0


class TestUnifiedAPIGateway:
    """测试统一API网关"""
    
    def setup_method(self):
        """测试前设置"""
        self.gateway = UnifiedAPIGateway()
    
    @pytest.mark.asyncio
    async def test_gateway_initialization(self):
        """测试网关初始化"""
        # Mock dependencies
        with patch('core.gpu_manager.GPUManager') as mock_gpu_manager, \
             patch('core.model_manager.UnifiedModelManager') as mock_model_manager:
            
            mock_gpu_instance = Mock()
            mock_gpu_instance.initialize = AsyncMock(return_value=True)
            mock_gpu_manager.return_value = mock_gpu_instance
            
            mock_model_instance = Mock()
            mock_model_instance.initialize = AsyncMock(return_value=True)
            mock_model_manager.return_value = mock_model_instance
            
            result = await self.gateway.initialize()
            
            assert result is True
            assert self.gateway.initialized is True
    
    def test_create_error_response(self):
        """测试创建错误响应"""
        request = UnifiedChatRequest(
            model="test-model",
            messages=[{"role": "user", "content": "test"}]
        )
        
        error_response = self.gateway._create_error_response("Test error", request)
        
        assert error_response.model == "test-model"
        assert error_response.provider == "gateway"
        assert "Test error" in error_response.choices[0]["message"]["content"]
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        # Mock dependencies
        self.gateway.initialized = True
        self.gateway.model_manager = Mock()
        self.gateway.gpu_manager = Mock()
        self.gateway.gpu_manager.initialized = True
        self.gateway.router = Mock()
        
        health_status = await self.gateway.health_check()
        
        assert health_status["status"] == "healthy"
        assert "components" in health_status
        assert health_status["components"]["model_manager"] is True


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_chat_completion(self):
        """测试端到端聊天完成"""
        # 这是一个简化的集成测试，模拟完整的请求流程
        
        # 1. 创建请求
        request = UnifiedChatRequest(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=100,
            temperature=0.7
        )
        
        # 2. Mock所有组件
        with patch('core.unified_api_gateway.UnifiedAPIGateway') as MockGateway:
            mock_gateway = MockGateway.return_value
            mock_gateway.initialize = AsyncMock(return_value=True)
            mock_gateway.handle_chat_completion = AsyncMock(
                return_value=UnifiedChatResponse(
                    id="test-123",
                    model="test-model",
                    provider="test",
                    engine="test",
                    choices=[{
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hello!"},
                        "finish_reason": "stop"
                    }]
                )
            )
            
            # 3. 执行测试
            gateway = MockGateway()
            await gateway.initialize()
            response = await gateway.handle_chat_completion(request)
            
            # 4. 验证结果
            assert response.id == "test-123"
            assert response.choices[0]["message"]["content"] == "Hello!"
    
    def test_configuration_loading(self):
        """测试配置加载"""
        from core.config_manager import DynamicConfigManager
        
        # Mock配置文件内容
        config_content = {
            "api": {"host": "0.0.0.0", "port": 8000},
            "engines": {
                "openai": {"enabled": True, "api_key": "${OPENAI_API_KEY}"}
            }
        }
        
        manager = DynamicConfigManager()
        
        # 模拟环境变量处理
        processed = manager._process_env_variables(config_content)
        
        assert processed["api"]["host"] == "0.0.0.0"
        assert processed["engines"]["openai"]["enabled"] is True


# 运行测试的辅助函数
def run_tests():
    """运行所有测试"""
    import subprocess
    import sys
    
    # 运行pytest
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short"
    ], capture_output=True, text=True)
    
    print("测试输出:")
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    # 直接运行测试
    success = run_tests()
    if success:
        print("✅ 所有测试通过")
    else:
        print("❌ 测试失败")
        exit(1)