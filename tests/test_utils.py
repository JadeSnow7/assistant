"""
测试基础类和共享工具
提供统一的测试基础设施
"""
import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from datetime import datetime


class TestLevel(Enum):
    """测试级别"""
    UNIT = "unit"
    INTEGRATION = "integration" 
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestResult(Enum):
    """测试结果"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestMetrics:
    """测试指标"""
    test_name: str
    test_level: TestLevel
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    network_requests: int = 0
    assertions_count: int = 0
    success: bool = True
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class BaseTestCase:
    """测试基类"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.start_time = None
        self.metrics: List[TestMetrics] = []
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger(f"test.{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def start_timer(self):
        """开始计时"""
        self.start_time = time.time()
    
    def stop_timer(self, test_name: str, test_level: TestLevel = TestLevel.UNIT) -> TestMetrics:
        """停止计时并记录指标"""
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        
        duration = (time.time() - self.start_time) * 1000
        metric = TestMetrics(
            test_name=test_name,
            test_level=test_level,
            duration_ms=duration
        )
        self.metrics.append(metric)
        self.start_time = None
        return metric
    
    def assert_performance(self, metric: TestMetrics, max_duration_ms: float):
        """性能断言"""
        assert metric.duration_ms <= max_duration_ms, (
            f"Test {metric.test_name} took {metric.duration_ms:.2f}ms, "
            f"expected <= {max_duration_ms}ms"
        )
    
    def log_metrics(self):
        """记录指标"""
        for metric in self.metrics:
            self.logger.info(f"Test metrics: {asdict(metric)}")


class MockAPIClient:
    """模拟API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = f"test-session-{int(time.time())}"
        self.call_count = 0
        self.last_request = None
        self.responses = {}
    
    def set_mock_response(self, endpoint: str, response: Dict[str, Any]):
        """设置模拟响应"""
        self.responses[endpoint] = response
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送POST请求"""
        self.call_count += 1
        self.last_request = {"endpoint": endpoint, "data": data}
        
        # 返回预设的模拟响应
        if endpoint in self.responses:
            return self.responses[endpoint]
        
        # 默认响应
        return {
            "status": "success",
            "message": f"Mock response for {endpoint}",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """发送GET请求"""
        self.call_count += 1
        self.last_request = {"endpoint": endpoint, "params": params}
        
        if endpoint in self.responses:
            return self.responses[endpoint]
        
        return {
            "status": "success",
            "data": f"Mock data for {endpoint}",
            "timestamp": datetime.now().isoformat()
        }


class MockModelEngine:
    """模拟模型引擎"""
    
    def __init__(self):
        self.loaded_models = {}
        self.inference_count = 0
        self.total_tokens = 0
        
    async def load_model(self, model_name: str, model_path: str = None) -> bool:
        """加载模型"""
        self.loaded_models[model_name] = {
            "path": model_path or f"/mock/path/{model_name}",
            "loaded_at": datetime.now().isoformat(),
            "parameters": {"vocab_size": 32000, "hidden_size": 4096}
        }
        return True
    
    async def unload_model(self, model_name: str) -> bool:
        """卸载模型"""
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            return True
        return False
    
    async def inference(self, model_name: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """推理"""
        if model_name not in self.loaded_models:
            raise ValueError(f"Model {model_name} not loaded")
        
        self.inference_count += 1
        tokens_generated = len(prompt.split()) * 2  # 模拟token生成
        self.total_tokens += tokens_generated
        
        return {
            "model": model_name,
            "prompt": prompt,
            "response": f"Mock response to: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
            "tokens_generated": tokens_generated,
            "inference_time_ms": 100,  # 模拟推理时间
            "confidence": 0.95,
            "finish_reason": "length",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": tokens_generated,
                "total_tokens": len(prompt.split()) + tokens_generated
            }
        }
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        return self.loaded_models.get(model_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "loaded_models": len(self.loaded_models),
            "total_inferences": self.inference_count,
            "total_tokens": self.total_tokens,
            "models": list(self.loaded_models.keys())
        }


class MockPluginManager:
    """模拟插件管理器"""
    
    def __init__(self):
        self.plugins = {}
        self.execution_count = 0
        
    async def register_plugin(self, name: str, config: Dict[str, Any]) -> bool:
        """注册插件"""
        self.plugins[name] = {
            "config": config,
            "enabled": True,
            "registered_at": datetime.now().isoformat(),
            "execution_count": 0
        }
        return True
    
    async def unregister_plugin(self, name: str) -> bool:
        """注销插件"""
        if name in self.plugins:
            del self.plugins[name]
            return True
        return False
    
    async def execute_plugin(self, name: str, method: str, **kwargs) -> Dict[str, Any]:
        """执行插件"""
        if name not in self.plugins:
            raise ValueError(f"Plugin {name} not registered")
        
        if not self.plugins[name]["enabled"]:
            raise ValueError(f"Plugin {name} is disabled")
        
        self.execution_count += 1
        self.plugins[name]["execution_count"] += 1
        
        return {
            "plugin": name,
            "method": method,
            "args": kwargs,
            "result": f"Mock result from {name}.{method}",
            "execution_time_ms": 50,
            "success": True
        }
    
    def list_plugins(self) -> Dict[str, Any]:
        """列出插件"""
        return {name: info for name, info in self.plugins.items()}
    
    async def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        if name in self.plugins:
            self.plugins[name]["enabled"] = True
            return True
        return False
    
    async def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        if name in self.plugins:
            self.plugins[name]["enabled"] = False
            return True
        return False


class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def create_chat_request(
        message: str = "Hello, AI!",
        session_id: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """创建聊天请求"""
        return {
            "message": message,
            "session_id": session_id or f"test-session-{int(time.time())}",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_plugin_config(
        name: str,
        version: str = "1.0.0",
        enabled: bool = True,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """创建插件配置"""
        return {
            "name": name,
            "version": version,
            "enabled": enabled,
            "config": config or {},
            "author": "Test Author",
            "description": f"Test plugin: {name}",
            "requirements": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "test_mode": True
            }
        }
    
    @staticmethod
    def create_system_status() -> Dict[str, Any]:
        """创建系统状态"""
        return {
            "status": "healthy",
            "version": "0.1.0-test",
            "uptime_seconds": 3600,
            "memory": {
                "used_mb": 256,
                "available_mb": 7680,
                "usage_percent": 3.2
            },
            "cpu": {
                "usage_percent": 15.5,
                "cores": 8
            },
            "models": {
                "loaded": 1,
                "available": 3
            },
            "plugins": {
                "loaded": 2,
                "enabled": 2
            },
            "connections": {
                "active": 1,
                "total": 42
            },
            "timestamp": datetime.now().isoformat()
        }


# 实用工具函数
def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """等待条件满足"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False


async def async_wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """异步等待条件满足"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    return False


def assert_dict_subset(subset: Dict, full_dict: Dict, path: str = ""):
    """断言字典子集"""
    for key, expected_value in subset.items():
        current_path = f"{path}.{key}" if path else key
        assert key in full_dict, f"Missing key: {current_path}"
        
        actual_value = full_dict[key]
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            assert_dict_subset(expected_value, actual_value, current_path)
        else:
            assert actual_value == expected_value, (
                f"Value mismatch at {current_path}: "
                f"expected {expected_value}, got {actual_value}"
            )


def create_temporary_config(config_dict: Dict[str, Any], temp_dir: str) -> Path:
    """创建临时配置文件"""
    config_path = Path(temp_dir) / "test_config.json"
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2)
    return config_path