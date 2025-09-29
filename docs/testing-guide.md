# NEX AI Assistant 测试指南

## 概述

本文档提供了NEX AI Assistant项目的完整测试指南，包括测试框架、测试类型、最佳实践和CI/CD流程。

## 目录

1. [测试架构](#测试架构)
2. [测试环境设置](#测试环境设置)
3. [测试类型](#测试类型)
4. [运行测试](#运行测试)
5. [编写测试](#编写测试)
6. [CI/CD集成](#cicd集成)
7. [性能测试](#性能测试)
8. [最佳实践](#最佳实践)
9. [故障排除](#故障排除)

## 测试架构

### 分层测试结构

项目采用标准的测试金字塔架构：

```
        E2E Tests
      ↗            ↖
Integration Tests    Security Tests
    ↗        ↖           ↗
Unit Tests    Performance Tests
```

### 目录结构

```
tests/
├── unit/                    # 单元测试
│   ├── core/               # 核心模块测试
│   ├── services/           # 服务层测试
│   └── interfaces/         # 接口层测试
├── integration/            # 集成测试
│   ├── api/               # API集成测试
│   ├── workflow/          # 工作流测试
│   └── cross_module/      # 跨模块测试
├── e2e/                   # 端到端测试
│   ├── cli/               # CLI端到端测试
│   ├── web/               # Web端到端测试
│   └── scenarios/         # 场景测试
├── performance/           # 性能测试
│   ├── load/              # 负载测试
│   ├── stress/            # 压力测试
│   └── benchmark/         # 基准测试
├── security/              # 安全测试
│   ├── auth/              # 认证测试
│   ├── input/             # 输入验证测试
│   └── vulnerability/     # 漏洞扫描
├── fixtures/              # 测试数据
├── conftest.py           # pytest配置
└── test_utils.py         # 测试工具
```

## 测试环境设置

### 1. 安装依赖

```bash
# 设置开发环境
make setup-dev

# 或手动安装
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements-dev.txt
```

### 2. 环境配置

创建测试环境配置文件：

```bash
# 复制环境配置
cp configs/environments/development.yaml configs/environments/test.yaml
```

编辑 `test.yaml` 配置测试专用设置：

```yaml
app:
  name: "nex-ai-test"
  debug: true
  environment: "test"

database:
  url: "sqlite:///:memory:"

redis:
  url: "redis://localhost:6379/15"  # 使用测试数据库

logging:
  level: "DEBUG"
  
models:
  local:
    provider: "mock"
  cloud:
    provider: "mock"
```

### 3. 验证环境

```bash
# 运行基础测试验证环境
make test-fast

# 或
pytest tests/test_basic.py -v
```

## 测试类型

### 单元测试 (Unit Tests)

测试单个模块或函数的功能。

**特点：**
- 快速执行
- 高覆盖率要求 (≥80%)
- 使用Mock对象隔离依赖
- 测试业务逻辑和边界条件

**示例：**

```python
@pytest.mark.unit
async def test_model_inference():
    engine = MockModelEngine()
    await engine.load_model("test-model")
    
    result = await engine.inference("test-model", "Hello")
    
    assert result["response"] is not None
    assert result["tokens_generated"] > 0
```

### 集成测试 (Integration Tests)

测试多个模块之间的交互。

**特点：**
- 测试模块间接口
- 验证数据流
- 可能需要真实依赖服务
- 覆盖率要求 (≥70%)

**示例：**

```python
@pytest.mark.integration
@pytest.mark.api
async def test_chat_workflow():
    async with aiohttp.ClientSession() as session:
        # 健康检查
        async with session.get(f"{base_url}/health") as resp:
            assert resp.status == 200
        
        # 聊天请求
        chat_data = {"message": "Hello", "session_id": "test"}
        async with session.post(f"{base_url}/api/v1/chat", json=chat_data) as resp:
            assert resp.status == 200
            response = await resp.json()
            assert "response" in response
```

### 端到端测试 (E2E Tests)

测试完整的用户场景。

**特点：**
- 从用户角度测试
- 覆盖关键业务流程
- 可能较慢
- 覆盖率要求 (≥90%关键路径)

### 性能测试 (Performance Tests)

测试系统性能指标。

**特点：**
- 负载测试
- 压力测试
- 基准测试
- 资源使用监控

### 安全测试 (Security Tests)

测试安全相关功能。

**特点：**
- 认证授权
- 输入验证
- 漏洞扫描
- 数据保护

## 运行测试

### 使用Makefile (推荐)

```bash
# 运行所有测试
make test

# 运行特定类型的测试
make test-unit           # 单元测试
make test-integration    # 集成测试
make test-e2e           # 端到端测试
make test-performance   # 性能测试
make test-security      # 安全测试

# 运行快速测试（跳过慢速测试）
make test-fast

# 生成覆盖率报告
make test-coverage

# 监视模式（文件变化自动运行）
make test-watch
```

### 使用pytest直接运行

```bash
# 基本用法
pytest tests/ -v

# 按标记运行
pytest -m "unit" -v                    # 只运行单元测试
pytest -m "not slow" -v                # 跳过慢速测试
pytest -m "unit and not network" -v    # 单元测试且不需要网络

# 按目录运行
pytest tests/unit/ -v                  # 单元测试目录
pytest tests/integration/ -v           # 集成测试目录

# 特定测试文件
pytest tests/unit/core/test_inference_engine.py -v

# 特定测试函数
pytest tests/unit/core/test_inference_engine.py::TestLocalInferenceEngine::test_model_loading -v

# 并行运行
pytest tests/ -n auto                  # 自动检测CPU核心数
pytest tests/ -n 4                     # 使用4个进程

# 生成报告
pytest tests/ --cov=core --cov=services --cov-report=html
pytest tests/ --junitxml=junit.xml     # CI/CD友好的XML报告
```

### 高级选项

```bash
# 调试模式
pytest tests/ -v -s --pdb             # 失败时进入调试器
pytest tests/ --lf                    # 只运行上次失败的测试
pytest tests/ --ff                    # 首先运行失败的测试

# 性能分析
pytest tests/ --benchmark-only        # 只运行基准测试
pytest tests/ --durations=10          # 显示最慢的10个测试

# 自定义选项
pytest tests/ --runslow              # 运行标记为slow的测试
pytest tests/ --runnetwork           # 运行需要网络的测试
```

## 编写测试

### 基本结构

使用提供的基础类：

```python
from tests.test_utils import BaseTestCase, TestLevel, TestDataFactory

class TestMyFeature(BaseTestCase):
    def setup_method(self):
        """每个测试方法前执行"""
        self.feature = MyFeature()
    
    @pytest.mark.unit
    async def test_basic_functionality(self):
        """测试基本功能"""
        self.start_timer()
        
        result = await self.feature.process("input")
        
        assert result is not None
        assert result["status"] == "success"
        
        metric = self.stop_timer("basic_functionality", TestLevel.UNIT)
        self.assert_performance(metric, 1000)  # 应在1秒内完成
```

### 使用Fixtures

```python
@pytest.fixture
def mock_client(mock_grpc_client):
    """使用配置的mock客户端"""
    return mock_client

@pytest.fixture
def sample_data():
    """提供测试数据"""
    return TestDataFactory.create_chat_request("Test message")

def test_with_fixtures(mock_client, sample_data):
    """使用fixtures的测试"""
    result = mock_client.process(sample_data)
    assert result["success"] is True
```

### 参数化测试

```python
@pytest.mark.parametrize("input_msg,expected", [
    ("Hello", "greeting"),
    ("What's the weather?", "weather"),
    ("Calculate 2+2", "math"),
])
def test_message_classification(input_msg, expected):
    classifier = MessageClassifier()
    result = classifier.classify(input_msg)
    assert result["category"] == expected
```

### Mock使用

```python
from unittest.mock import AsyncMock, patch

@patch('module.external_service')
async def test_with_external_service(mock_service):
    """测试外部服务调用"""
    mock_service.call_api = AsyncMock(return_value={"status": "ok"})
    
    service = MyService()
    result = await service.process_with_external()
    
    assert result["status"] == "ok"
    mock_service.call_api.assert_called_once()
```

### 性能测试编写

```python
@pytest.mark.performance
class TestPerformance(PerformanceTestBase):
    @pytest.mark.asyncio
    async def test_load_performance(self):
        """负载性能测试"""
        async def make_request():
            # 单个请求逻辑
            return await self.api_client.post("/api/endpoint", data)
        
        # 运行负载测试
        results = await self.run_concurrent_requests(
            make_request, num_requests=100, concurrency=20
        )
        
        metrics = self.analyze_results("Load Test", results, test_duration)
        
        # 性能断言
        assert metrics.error_rate <= 5.0
        assert metrics.avg_response_time <= 1000
        assert metrics.requests_per_second >= 50
```

## CI/CD集成

### GitHub Actions工作流

项目包含以下GitHub Actions工作流：

1. **质量门禁** (`.github/workflows/quality-gate.yml`)
   - 代码格式检查
   - 类型检查
   - 安全扫描
   - 快速测试

2. **CI/CD流水线** (`.github/workflows/ci-cd.yml`)
   - 测试矩阵
   - 构建验证
   - 部署流程

### 本地CI模拟

```bash
# 模拟CI环境测试
make ci-test

# 检查是否通过质量门禁
make pre-commit
```

### 分支策略

- `main`: 生产分支，所有测试必须通过
- `develop`: 开发分支，单元测试和集成测试必须通过
- 特性分支：质量门禁必须通过

## 性能测试

### 性能测试类型

1. **负载测试**：正常负载下的性能
2. **压力测试**：高负载下的稳定性
3. **容量测试**：系统容量上限
4. **稳定性测试**：长时间运行稳定性

### 性能指标

| 指标 | 目标值 | 监控方式 |
|-----|--------|---------|
| API响应时间(P95) | < 500ms | 自动化测试 |
| 本地推理延迟(P95) | < 2s | 性能测试 |
| 云端推理延迟(P95) | < 5s | 集成测试 |
| 错误率 | < 0.1% | 监控告警 |
| 吞吐量 | > 100 RPS | 负载测试 |
| CPU使用率 | < 80% | 系统监控 |
| 内存使用率 | < 85% | 系统监控 |

### 运行性能测试

```bash
# 运行所有性能测试
make test-performance

# 运行特定性能测试
pytest tests/performance/ -k load -v
pytest tests/performance/ -k stress -v

# 生成性能报告
pytest tests/performance/ --benchmark-save=latest
```

## 最佳实践

### 测试编写原则

1. **FIRST原则**
   - **Fast**: 测试应该快速执行
   - **Independent**: 测试之间应该独立
   - **Repeatable**: 测试应该可重复
   - **Self-Validating**: 测试应该有明确的通过/失败结果
   - **Timely**: 测试应该及时编写

2. **AAA模式**
   - **Arrange**: 准备测试数据和环境
   - **Act**: 执行被测试的操作
   - **Assert**: 验证结果

3. **命名规范**
   ```python
   def test_should_return_error_when_input_is_invalid():
       """测试名称应该描述预期行为"""
       pass
   ```

### 测试数据管理

1. **使用Factory模式**
   ```python
   # 使用TestDataFactory创建测试数据
   chat_request = TestDataFactory.create_chat_request(
       message="test message",
       session_id="test-session"
   )
   ```

2. **避免硬编码**
   ```python
   # 不好的方式
   assert response["tokens"] == 42
   
   # 好的方式
   assert response["tokens"] > 0
   assert response["tokens"] < 1000
   ```

3. **使用Fixtures管理共享数据**
   ```python
   @pytest.fixture(scope="session")
   def test_database():
       """会话级别的测试数据库"""
       db = create_test_database()
       yield db
       cleanup_database(db)
   ```

### Mock策略

1. **Mock外部依赖**
   - 网络请求
   - 数据库调用
   - 文件系统操作
   - 时间相关函数

2. **保持Mock简单**
   ```python
   # 简单有效的Mock
   mock_service.return_value = {"status": "success"}
   
   # 避免过于复杂的Mock逻辑
   ```

3. **验证Mock调用**
   ```python
   mock_service.assert_called_once_with(expected_params)
   assert mock_service.call_count == 2
   ```

### 性能测试最佳实践

1. **建立性能基线**
   ```python
   # 记录基准性能
   baseline_metrics = load_baseline_metrics()
   assert current_metrics.response_time <= baseline_metrics.response_time * 1.1
   ```

2. **渐进式性能测试**
   ```python
   # 从小负载开始，逐步增加
   for load_level in [10, 50, 100, 200]:
       metrics = run_load_test(requests=load_level)
       assert metrics.error_rate <= 1.0
   ```

3. **监控资源使用**
   ```python
   # 监控系统资源
   initial_memory = get_memory_usage()
   run_test()
   final_memory = get_memory_usage()
   assert final_memory - initial_memory < memory_threshold
   ```

## 故障排除

### 常见问题

1. **ModuleNotFoundError**
   ```bash
   # 确保PYTHONPATH正确
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   
   # 或安装为可编辑包
   pip install -e .
   ```

2. **数据库连接错误**
   ```bash
   # 检查测试数据库配置
   # 使用内存数据库避免冲突
   DATABASE_URL=sqlite:///:memory: pytest tests/
   ```

3. **端口冲突**
   ```bash
   # 使用随机端口或检查端口占用
   lsof -i :8000
   
   # 或在测试中使用随机端口
   TEST_PORT=$(python -c "import socket; s=socket.socket(); s.bind(('', 0)); print(s.getsockname()[1]); s.close()")
   ```

4. **测试超时**
   ```python
   # 为慢速测试设置超时
   @pytest.mark.timeout(60)
   def test_slow_operation():
       pass
   
   # 或使用asyncio超时
   async with asyncio.timeout(30):
       await slow_operation()
   ```

### 调试技巧

1. **使用pytest调试**
   ```bash
   # 进入调试器
   pytest tests/test_file.py::test_function -v -s --pdb
   
   # 只运行失败的测试
   pytest --lf -v -s --pdb
   ```

2. **增加日志输出**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   def test_with_debug_logs():
       logger = logging.getLogger(__name__)
       logger.debug("Debug information")
       # 测试逻辑
   ```

3. **临时跳过测试**
   ```python
   @pytest.mark.skip(reason="Debugging other tests")
   def test_temporarily_disabled():
       pass
   
   @pytest.mark.skipif(condition, reason="Skip on certain condition")
   def test_conditional_skip():
       pass
   ```

### 性能问题诊断

1. **识别慢速测试**
   ```bash
   # 显示最慢的测试
   pytest --durations=10
   
   # 性能分析
   python -m cProfile -o profile.stats pytest tests/
   ```

2. **内存泄漏检测**
   ```bash
   # 使用memory_profiler
   pip install memory-profiler
   
   # 监控内存使用
   @profile
   def test_memory_usage():
       # 测试逻辑
       pass
   ```

3. **并发问题诊断**
   ```python
   # 检查并发安全
   import threading
   
   def test_thread_safety():
       results = []
       threads = []
       
       def worker():
           result = thread_unsafe_function()
           results.append(result)
       
       for _ in range(10):
           t = threading.Thread(target=worker)
           threads.append(t)
           t.start()
       
       for t in threads:
           t.join()
       
       # 验证结果一致性
       assert len(set(results)) == 1
   ```

## 附录

### 测试配置文件示例

**pytest.ini**
```ini
[tool:pytest]
minversion = 7.0
addopts = 
    --strict-markers
    --strict-config
    -ra
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow running tests
    network: Tests requiring network access
```

### 有用的pytest插件

- `pytest-cov`: 代码覆盖率
- `pytest-xdist`: 并行测试
- `pytest-mock`: Mock工具
- `pytest-asyncio`: 异步测试支持
- `pytest-benchmark`: 基准测试
- `pytest-timeout`: 测试超时
- `pytest-html`: HTML测试报告

### 资源链接

- [pytest官方文档](https://docs.pytest.org/)
- [Python测试最佳实践](https://realpython.com/python-testing/)
- [Mock使用指南](https://docs.python.org/3/library/unittest.mock.html)
- [性能测试指南](https://github.com/ionelmc/pytest-benchmark)

---

**更新日期**: 2024-01-20  
**版本**: 1.0.0  
**维护者**: NEX开发团队