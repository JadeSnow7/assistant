"""
pytest配置文件
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path

# 添加项目根目录到Python路径
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_config():
    """测试配置"""
    return {
        "app": {
            "name": "test-ai-assistant",
            "debug": True,
            "environment": "test"
        },
        "server": {
            "host": "localhost",
            "port": 18000
        },
        "database": {
            "url": "sqlite:///:memory:"
        },
        "models": {
            "local": {
                "provider": "mock",
                "model_path": "test-model"
            },
            "cloud": {
                "provider": "mock",
                "api_key": "test-key"
            }
        }
    }


@pytest.fixture
def mock_grpc_client():
    """模拟gRPC客户端"""
    class MockGRPCClient:
        def __init__(self):
            self.connected = False
        
        async def connect(self):
            self.connected = True
            return True
        
        async def disconnect(self):
            self.connected = False
        
        async def health_check(self):
            return self.connected
        
        async def inference(self, request):
            return {
                "text": f"Mock response to: {request.get('prompt', '')}",
                "finished": True,
                "confidence": 0.9
            }
    
    return MockGRPCClient()