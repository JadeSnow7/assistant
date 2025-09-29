"""
pytest配置文件 - 改进版
提供完整的测试环境配置和fixtures
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
import logging
from typing import Dict, Any, Optional, Generator
from unittest.mock import AsyncMock, MagicMock
import json
import time
from datetime import datetime

# 添加项目根目录到Python路径
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "python"))

# 设置测试日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """测试配置"""
    return {
        "app": {
            "name": "test-ai-assistant",
            "debug": True,
            "environment": "test",
            "log_level": "DEBUG"
        },
        "server": {
            "host": "localhost",
            "port": 18000,
            "timeout": 30
        },
        "database": {
            "url": "sqlite:///:memory:",
            "echo": False
        },
        "models": {
            "local": {
                "provider": "mock",
                "model_path": "test-model",
                "max_tokens": 1000,
                "temperature": 0.7
            },
            "cloud": {
                "provider": "mock",
                "api_key": "test-key",
                "base_url": "https://api.test.com"
            }
        },
        "redis": {
            "url": "redis://localhost:6379/15",  # 使用测试数据库
            "timeout": 5
        },
        "plugins": {
            "enabled": True,
            "directory": "plugins",
            "timeout": 30
        }
    }


@pytest.fixture
def mock_grpc_client():
    """模拟gRPC客户端"""
    class MockGRPCClient:
        def __init__(self):
            self.connected = False
            self.call_count = 0
            self.last_request = None
        
        async def connect(self):
            self.connected = True
            return True
        
        async def disconnect(self):
            self.connected = False
        
        async def health_check(self):
            return {"status": "healthy" if self.connected else "unhealthy"}
        
        async def inference(self, request):
            self.call_count += 1
            self.last_request = request
            return {
                "text": f"Mock response to: {request.get('prompt', '')}",
                "finished": True,
                "confidence": 0.9,
                "model": "test-model",
                "tokens_used": 42,
                "response_time": 0.1
            }
    
    return MockGRPCClient()


@pytest.fixture
def mock_redis_client():
    """模拟Redis客户端"""
    class MockRedisClient:
        def __init__(self):
            self.data = {}
            self.connected = True
        
        async def get(self, key: str) -> Optional[str]:
            return self.data.get(key)
        
        async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
            self.data[key] = value
            return True
        
        async def delete(self, key: str) -> int:
            if key in self.data:
                del self.data[key]
                return 1
            return 0
        
        async def exists(self, key: str) -> int:
            return 1 if key in self.data else 0
        
        async def ping(self) -> bool:
            return self.connected
    
    return MockRedisClient()


@pytest.fixture
def mock_model_engine():
    """模拟模型推理引擎"""
    class MockModelEngine:
        def __init__(self):
            self.loaded = False
            self.model_name = "test-model"
            self.inference_count = 0
        
        async def load_model(self, model_path: str) -> bool:
            self.loaded = True
            return True
        
        async def unload_model(self) -> bool:
            self.loaded = False
            return True
        
        async def inference(self, prompt: str, **kwargs) -> Dict[str, Any]:
            if not self.loaded:
                raise RuntimeError("Model not loaded")
            
            self.inference_count += 1
            return {
                "response": f"Test response to: {prompt}",
                "tokens_generated": len(prompt.split()) * 2,
                "inference_time": 0.1,
                "model": self.model_name
            }
    
    return MockModelEngine()


@pytest.fixture
def mock_plugin_manager():
    """模拟插件管理器"""
    class MockPluginManager:
        def __init__(self):
            self.plugins = {}
            self.enabled = True
        
        async def load_plugin(self, plugin_name: str) -> bool:
            self.plugins[plugin_name] = {"loaded": True, "active": True}
            return True
        
        async def unload_plugin(self, plugin_name: str) -> bool:
            if plugin_name in self.plugins:
                self.plugins[plugin_name]["loaded"] = False
                return True
            return False
        
        async def execute_plugin(self, plugin_name: str, method: str, **kwargs) -> Dict[str, Any]:
            if plugin_name not in self.plugins or not self.plugins[plugin_name]["loaded"]:
                raise RuntimeError(f"Plugin {plugin_name} not loaded")
            
            return {
                "plugin": plugin_name,
                "method": method,
                "result": f"Mock result from {plugin_name}.{method}",
                "success": True
            }
        
        def list_plugins(self) -> Dict[str, Any]:
            return self.plugins
    
    return MockPluginManager()


@pytest.fixture
def sample_test_data():
    """示例测试数据"""
    return {
        "chat_requests": [
            {
                "message": "Hello, how are you?",
                "session_id": "test-session-1", 
                "max_tokens": 100
            },
            {
                "message": "What is the weather like?",
                "session_id": "test-session-2",
                "max_tokens": 200
            }
        ],
        "plugin_configs": [
            {
                "name": "weather",
                "version": "1.0.0",
                "enabled": True,
                "config": {"api_key": "test-key"}
            },
            {
                "name": "calculator",
                "version": "1.0.0", 
                "enabled": True,
                "config": {}
            }
        ],
        "shell_commands": [
            "help",
            "status",
            "chat hello world",
            "plugin list",
            "system info"
        ]
    }


@pytest.fixture
def performance_monitor():
    """性能监控工具"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.metrics = []
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self, operation_name: str = "test"):
            if self.start_time is None:
                raise RuntimeError("Monitor not started")
            
            duration = time.time() - self.start_time
            metric = {
                "operation": operation_name,
                "duration_ms": duration * 1000,
                "timestamp": datetime.now().isoformat()
            }
            self.metrics.append(metric)
            self.start_time = None
            return metric
        
        def get_metrics(self):
            return self.metrics
        
        def clear(self):
            self.metrics.clear()
    
    return PerformanceMonitor()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """自动设置测试环境"""
    # 设置测试环境变量
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DISABLE_TELEMETRY", "true")
    monkeypatch.setenv("TEST_MODE", "true")
    
    # 确保不会意外连接到生产服务
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    
    yield
    
    # 清理可能存在的状态
    logger.info("Test environment cleanup completed")


# pytest插件钩子
def pytest_configure(config):
    """pytest配置钩子"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access" 
    )
    config.addinivalue_line(
        "markers", "gpu: mark test as requiring GPU access"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    # 为没有标记的测试添加unit标记
    for item in items:
        if not any(mark.name in ["unit", "integration", "e2e", "performance"] 
                  for mark in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


def pytest_runtest_setup(item):
    """测试运行前设置"""
    # 跳过标记为slow的测试（除非明确要求运行）
    if "slow" in [mark.name for mark in item.iter_markers()]:
        if not item.config.getoption("--runslow", default=False):
            pytest.skip("need --runslow option to run")


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--runnetwork",
        action="store_true", 
        default=False,
        help="run tests that require network access"
    )