"""
推理引擎核心功能单元测试
测试本地模型推理、云端适配、智能路由等功能
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from tests.test_utils import BaseTestCase, MockModelEngine, TestLevel, TestDataFactory


class TestLocalInferenceEngine(BaseTestCase):
    """本地推理引擎测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.engine = MockModelEngine()
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_model_loading(self):
        """测试模型加载"""
        self.start_timer()
        
        # 测试成功加载
        result = await self.engine.load_model("test-model", "/path/to/model")
        assert result is True
        
        # 验证模型已加载
        model_info = self.engine.get_model_info("test-model")
        assert model_info is not None
        assert model_info["path"] == "/path/to/model"
        
        metric = self.stop_timer("model_loading", TestLevel.UNIT)
        self.assert_performance(metric, 1000)  # 应该在1秒内完成
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_model_unloading(self):
        """测试模型卸载"""
        # 先加载模型
        await self.engine.load_model("test-model")
        assert "test-model" in self.engine.loaded_models
        
        # 测试卸载
        result = await self.engine.unload_model("test-model")
        assert result is True
        assert "test-model" not in self.engine.loaded_models
        
        # 测试卸载不存在的模型
        result = await self.engine.unload_model("non-existent")
        assert result is False
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_basic_inference(self):
        """测试基础推理功能"""
        # 先加载模型
        await self.engine.load_model("test-model")
        
        self.start_timer()
        
        # 执行推理
        result = await self.engine.inference(
            model_name="test-model",
            prompt="What is the capital of France?",
            max_tokens=100,
            temperature=0.7
        )
        
        # 验证结果
        assert result["model"] == "test-model"
        assert "response" in result
        assert result["tokens_generated"] > 0
        assert result["confidence"] > 0
        assert "usage" in result
        
        metric = self.stop_timer("basic_inference", TestLevel.UNIT)
        self.assert_performance(metric, 2000)  # 推理应该在2秒内完成
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_inference_without_loaded_model(self):
        """测试未加载模型时的推理"""
        with pytest.raises(ValueError, match="Model .* not loaded"):
            await self.engine.inference("non-existent", "test prompt")
            
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_concurrent_inference(self):
        """测试并发推理"""
        await self.engine.load_model("test-model")
        
        # 并发推理任务
        tasks = [
            self.engine.inference("test-model", f"Prompt {i}")
            for i in range(5)
        ]
        
        self.start_timer()
        results = await asyncio.gather(*tasks)
        metric = self.stop_timer("concurrent_inference", TestLevel.UNIT)
        
        # 验证所有推理都成功
        assert len(results) == 5
        for i, result in enumerate(results):
            assert f"Prompt {i}" in result["prompt"]
            assert result["model"] == "test-model"
            
        # 验证统计信息
        stats = self.engine.get_stats()
        assert stats["total_inferences"] == 5
        
        self.assert_performance(metric, 5000)  # 并发推理应该在5秒内完成
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_memory_management(self):
        """测试内存管理"""
        # 加载多个模型
        models = ["model1", "model2", "model3"]
        for model in models:
            await self.engine.load_model(model)
            
        stats = self.engine.get_stats()
        assert stats["loaded_models"] == 3
        
        # 卸载部分模型
        await self.engine.unload_model("model2")
        
        stats = self.engine.get_stats()
        assert stats["loaded_models"] == 2
        assert "model2" not in stats["models"]
        assert "model1" in stats["models"]
        assert "model3" in stats["models"]


class TestCloudInferenceAdapter(BaseTestCase):
    """云端推理适配器测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.adapter = MockCloudAdapter()
        
    @pytest.mark.unit
    @pytest.mark.inference
    @pytest.mark.network
    async def test_openai_adapter(self):
        """测试OpenAI适配器"""
        self.start_timer()
        
        result = await self.adapter.inference(
            provider="openai",
            model="gpt-3.5-turbo",
            prompt="Hello, world!",
            api_key="test-key"
        )
        
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-3.5-turbo"
        assert "response" in result
        
        metric = self.stop_timer("openai_adapter", TestLevel.UNIT)
        self.assert_performance(metric, 3000)
        
    @pytest.mark.unit
    @pytest.mark.inference
    @pytest.mark.network
    async def test_gemini_adapter(self):
        """测试Gemini适配器"""
        result = await self.adapter.inference(
            provider="gemini",
            model="gemini-pro",
            prompt="Explain quantum computing",
            api_key="test-key"
        )
        
        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-pro"
        assert "response" in result
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_adapter_fallback(self):
        """测试适配器降级机制"""
        # 模拟主服务失败
        self.adapter.set_provider_status("openai", False)
        
        result = await self.adapter.inference_with_fallback(
            primary_provider="openai",
            fallback_provider="gemini",
            model="gpt-3.5-turbo",
            prompt="Test fallback"
        )
        
        # 应该使用降级服务
        assert result["provider"] == "gemini"
        assert result["fallback_used"] is True
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_rate_limiting(self):
        """测试限流机制"""
        # 快速发送多个请求
        tasks = [
            self.adapter.inference("openai", "gpt-3.5-turbo", f"Prompt {i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有请求被限流
        rate_limited = sum(1 for r in results if isinstance(r, Exception) and "rate limit" in str(r))
        successful = sum(1 for r in results if isinstance(r, dict) and "response" in r)
        
        assert successful + rate_limited == 10
        assert rate_limited > 0  # 应该有一些请求被限流


class TestIntelligentRouter(BaseTestCase):
    """智能路由器测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.router = MockIntelligentRouter()
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_simple_task_routing(self):
        """测试简单任务路由"""
        result = await self.router.route_request(
            prompt="What is 2+2?",
            complexity_threshold=0.3
        )
        
        # 简单任务应该路由到本地模型
        assert result["route"] == "local"
        assert result["model_type"] == "small"
        assert result["reasoning"] == "simple_task"
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_complex_task_routing(self):
        """测试复杂任务路由"""
        result = await self.router.route_request(
            prompt="Write a comprehensive analysis of quantum computing's impact on cryptography, including technical details and future implications.",
            complexity_threshold=0.3
        )
        
        # 复杂任务应该路由到云端大模型
        assert result["route"] == "cloud"
        assert result["model_type"] == "large"
        assert result["reasoning"] == "complex_task"
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_resource_aware_routing(self):
        """测试资源感知路由"""
        # 模拟高资源使用
        self.router.set_system_load(cpu_percent=90, memory_percent=85)
        
        result = await self.router.route_request(
            prompt="Medium complexity task",
            complexity_threshold=0.5
        )
        
        # 高负载时应该优先使用云端
        assert result["route"] == "cloud"
        assert result["reasoning"] == "high_system_load"
        
    @pytest.mark.unit
    @pytest.mark.inference
    async def test_cost_optimization_routing(self):
        """测试成本优化路由"""
        # 设置成本敏感模式
        result = await self.router.route_request(
            prompt="Generate a simple response",
            cost_sensitive=True
        )
        
        # 成本敏感时应该优先本地
        assert result["route"] == "local"
        assert "cost_optimized" in result["reasoning"]


# Mock classes for testing
class MockCloudAdapter:
    """模拟云端适配器"""
    
    def __init__(self):
        self.provider_status = {
            "openai": True,
            "gemini": True,
            "claude": True
        }
        self.request_count = {}
        
    def set_provider_status(self, provider: str, status: bool):
        self.provider_status[provider] = status
        
    async def inference(self, provider: str, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.provider_status.get(provider, True):
            raise Exception(f"Provider {provider} is unavailable")
            
        # 模拟限流
        self.request_count[provider] = self.request_count.get(provider, 0) + 1
        if self.request_count[provider] > 5:
            raise Exception(f"Rate limit exceeded for {provider}")
            
        return {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "response": f"Mock response from {provider}:{model}",
            "tokens_used": len(prompt.split()) * 2,
            "cost_cents": 0.1
        }
        
    async def inference_with_fallback(self, primary_provider: str, fallback_provider: str, **kwargs) -> Dict[str, Any]:
        try:
            result = await self.inference(primary_provider, **kwargs)
            result["fallback_used"] = False
            return result
        except Exception:
            result = await self.inference(fallback_provider, **kwargs)
            result["fallback_used"] = True
            return result


class MockIntelligentRouter:
    """模拟智能路由器"""
    
    def __init__(self):
        self.system_load = {"cpu_percent": 20, "memory_percent": 30}
        
    def set_system_load(self, cpu_percent: int, memory_percent: int):
        self.system_load = {"cpu_percent": cpu_percent, "memory_percent": memory_percent}
        
    async def route_request(self, prompt: str, complexity_threshold: float = 0.5, cost_sensitive: bool = False) -> Dict[str, Any]:
        # 分析任务复杂度
        complexity = self._analyze_complexity(prompt)
        
        # 检查系统负载
        high_load = self.system_load["cpu_percent"] > 80 or self.system_load["memory_percent"] > 80
        
        # 路由决策
        if high_load:
            return {
                "route": "cloud",
                "model_type": "large",
                "reasoning": "high_system_load",
                "complexity": complexity
            }
        elif cost_sensitive:
            return {
                "route": "local",
                "model_type": "small",
                "reasoning": "cost_optimized",
                "complexity": complexity
            }
        elif complexity < complexity_threshold:
            return {
                "route": "local", 
                "model_type": "small",
                "reasoning": "simple_task",
                "complexity": complexity
            }
        else:
            return {
                "route": "cloud",
                "model_type": "large", 
                "reasoning": "complex_task",
                "complexity": complexity
            }
            
    def _analyze_complexity(self, prompt: str) -> float:
        """分析提示复杂度"""
        word_count = len(prompt.split())
        complex_words = ["analysis", "comprehensive", "technical", "implications", "quantum", "cryptography"]
        complex_word_count = sum(1 for word in prompt.lower().split() if word in complex_words)
        
        # 简单的复杂度计算
        base_complexity = min(word_count / 100, 1.0)
        complexity_bonus = complex_word_count * 0.2
        
        return min(base_complexity + complexity_bonus, 1.0)