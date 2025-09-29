"""
性能测试实现
包括负载测试、基准测试、压力测试等
"""
import pytest
import asyncio
import aiohttp
import time
import psutil
import concurrent.futures
from typing import Dict, Any, List
import statistics
from dataclasses import dataclass
import json

from tests.test_utils import BaseTestCase, TestLevel, TestDataFactory


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    requests_per_second: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    test_duration: float


class PerformanceTestBase(BaseTestCase):
    """性能测试基类"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://localhost:8000"
        self.results: List[PerformanceMetrics] = []
        
    def calculate_percentile(self, data: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        return statistics.quantiles(sorted(data), n=100)[int(percentile) - 1]
    
    async def run_concurrent_requests(self, request_func, num_requests: int, 
                                    concurrency: int = 10) -> List[Dict[str, Any]]:
        """运行并发请求"""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request():
            async with semaphore:
                return await request_func()
        
        tasks = [bounded_request() for _ in range(num_requests)]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def analyze_results(self, test_name: str, results: List[Dict[str, Any]], 
                       test_duration: float) -> PerformanceMetrics:
        """分析测试结果"""
        successful_results = [r for r in results if isinstance(r, dict) and not r.get('error')]
        failed_results = [r for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get('error'))]
        
        response_times = [r.get('response_time_ms', 0) for r in successful_results]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = self.calculate_percentile(response_times, 95)
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0
        
        total_requests = len(results)
        successful_requests = len(successful_results)
        failed_requests = len(failed_results)
        error_rate = (failed_requests / total_requests) * 100 if total_requests > 0 else 0
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        # 获取系统资源使用情况
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_usage = process.cpu_percent()
        
        metrics = PerformanceMetrics(
            test_name=test_name,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            test_duration=test_duration
        )
        
        self.results.append(metrics)
        return metrics
    
    def report_metrics(self, metrics: PerformanceMetrics):
        """报告性能指标"""
        self.logger.info(f"Performance Metrics for {metrics.test_name}:")
        self.logger.info(f"  Total Requests: {metrics.total_requests}")
        self.logger.info(f"  Successful: {metrics.successful_requests}")
        self.logger.info(f"  Failed: {metrics.failed_requests}")
        self.logger.info(f"  Error Rate: {metrics.error_rate:.2f}%")
        self.logger.info(f"  Avg Response Time: {metrics.avg_response_time:.2f}ms")
        self.logger.info(f"  P95 Response Time: {metrics.p95_response_time:.2f}ms")
        self.logger.info(f"  Requests/sec: {metrics.requests_per_second:.2f}")
        self.logger.info(f"  Memory Usage: {metrics.memory_usage_mb:.2f}MB")
        self.logger.info(f"  CPU Usage: {metrics.cpu_usage_percent:.2f}%")


@pytest.mark.performance
class TestChatAPIPerformance(PerformanceTestBase):
    """聊天API性能测试"""
    
    @pytest.mark.asyncio
    async def test_chat_api_load(self):
        """聊天API负载测试"""
        async def make_chat_request():
            start_time = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    chat_data = TestDataFactory.create_chat_request(
                        message="Performance test message",
                        session_id=f"perf-test-{int(time.time())}"
                    )
                    
                    async with session.post(f"{self.base_url}/api/v1/chat", 
                                          json=chat_data, timeout=30) as resp:
                        response_time = (time.time() - start_time) * 1000
                        
                        if resp.status == 200:
                            data = await resp.json()
                            return {
                                "success": True,
                                "response_time_ms": response_time,
                                "status_code": resp.status,
                                "response_size": len(str(data))
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {resp.status}",
                                "response_time_ms": response_time
                            }
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "error": str(e),
                    "response_time_ms": response_time
                }
        
        # 运行负载测试
        num_requests = 100
        concurrency = 20
        
        start_time = time.time()
        results = await self.run_concurrent_requests(
            make_chat_request, num_requests, concurrency
        )
        test_duration = time.time() - start_time
        
        # 分析结果
        metrics = self.analyze_results("Chat API Load Test", results, test_duration)
        self.report_metrics(metrics)
        
        # 性能断言
        assert metrics.error_rate <= 5.0, f"Error rate too high: {metrics.error_rate}%"
        assert metrics.avg_response_time <= 2000, f"Average response time too slow: {metrics.avg_response_time}ms"
        assert metrics.p95_response_time <= 5000, f"P95 response time too slow: {metrics.p95_response_time}ms"
        assert metrics.requests_per_second >= 10, f"Throughput too low: {metrics.requests_per_second} req/s"
    
    @pytest.mark.asyncio
    async def test_chat_api_stress(self):
        """聊天API压力测试"""
        async def make_chat_request():
            start_time = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    # 使用更大的消息负载
                    large_message = "This is a stress test message. " * 100  # 约3KB消息
                    chat_data = TestDataFactory.create_chat_request(
                        message=large_message,
                        session_id=f"stress-test-{int(time.time())}-{asyncio.current_task().get_name()}",
                        max_tokens=500
                    )
                    
                    async with session.post(f"{self.base_url}/api/v1/chat", 
                                          json=chat_data, timeout=60) as resp:
                        response_time = (time.time() - start_time) * 1000
                        
                        if resp.status == 200:
                            data = await resp.json()
                            return {
                                "success": True,
                                "response_time_ms": response_time,
                                "status_code": resp.status,
                                "tokens_used": data.get("tokens_used", 0)
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {resp.status}",
                                "response_time_ms": response_time
                            }
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "error": str(e),
                    "response_time_ms": response_time
                }
        
        # 运行压力测试
        num_requests = 50
        concurrency = 30  # 更高并发
        
        start_time = time.time()
        results = await self.run_concurrent_requests(
            make_chat_request, num_requests, concurrency
        )
        test_duration = time.time() - start_time
        
        # 分析结果
        metrics = self.analyze_results("Chat API Stress Test", results, test_duration)
        self.report_metrics(metrics)
        
        # 压力测试的容忍度更高
        assert metrics.error_rate <= 10.0, f"Error rate too high: {metrics.error_rate}%"
        assert metrics.avg_response_time <= 5000, f"Average response time too slow: {metrics.avg_response_time}ms"
    
    @pytest.mark.asyncio
    async def test_streaming_performance(self):
        """流式API性能测试"""
        async def make_stream_request():
            start_time = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    chat_data = TestDataFactory.create_chat_request(
                        message="Tell me a story for performance testing",
                        session_id=f"stream-test-{int(time.time())}",
                        stream=True
                    )
                    
                    chunk_count = 0
                    first_chunk_time = None
                    
                    async with session.post(f"{self.base_url}/api/v1/chat/stream", 
                                          json=chat_data, timeout=60) as resp:
                        if resp.status == 200:
                            async for chunk in resp.content.iter_chunked(1024):
                                if chunk:
                                    chunk_count += 1
                                    if first_chunk_time is None:
                                        first_chunk_time = (time.time() - start_time) * 1000
                        
                        total_time = (time.time() - start_time) * 1000
                        
                        return {
                            "success": True,
                            "response_time_ms": total_time,
                            "first_chunk_time_ms": first_chunk_time or total_time,
                            "chunk_count": chunk_count,
                            "status_code": resp.status
                        }
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "error": str(e),
                    "response_time_ms": response_time
                }
        
        # 运行流式测试
        num_requests = 20
        concurrency = 5  # 较低并发，因为流式连接资源消耗大
        
        start_time = time.time()
        results = await self.run_concurrent_requests(
            make_stream_request, num_requests, concurrency
        )
        test_duration = time.time() - start_time
        
        # 分析结果
        metrics = self.analyze_results("Streaming API Performance", results, test_duration)
        self.report_metrics(metrics)
        
        # 流式API的性能要求
        assert metrics.error_rate <= 5.0, f"Error rate too high: {metrics.error_rate}%"
        
        # 检查首字节时间
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        if successful_results:
            first_chunk_times = [r.get('first_chunk_time_ms', 0) for r in successful_results]
            avg_first_chunk_time = statistics.mean(first_chunk_times)
            assert avg_first_chunk_time <= 1000, f"First chunk time too slow: {avg_first_chunk_time}ms"


@pytest.mark.performance
class TestSystemResourcePerformance(PerformanceTestBase):
    """系统资源性能测试"""
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """内存使用稳定性测试"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        async def make_request():
            async with aiohttp.ClientSession() as session:
                # 创建不同大小的请求
                message_sizes = ["Short message", "Medium message " * 10, "Long message " * 100]
                message = message_sizes[len(asyncio.all_tasks()) % len(message_sizes)]
                
                chat_data = TestDataFactory.create_chat_request(
                    message=message,
                    session_id=f"memory-test-{int(time.time())}"
                )
                
                async with session.post(f"{self.base_url}/api/v1/chat", 
                                      json=chat_data, timeout=30) as resp:
                    if resp.status == 200:
                        await resp.json()
                    return {"success": resp.status == 200}
        
        # 分批运行请求以观察内存变化
        batch_size = 20
        num_batches = 5
        memory_measurements = []
        
        for batch in range(num_batches):
            start_time = time.time()
            results = await self.run_concurrent_requests(make_request, batch_size, 10)
            batch_duration = time.time() - start_time
            
            # 记录内存使用
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory)
            
            self.logger.info(f"Batch {batch + 1}: Memory usage = {current_memory:.2f}MB")
            
            # 短暂等待让GC运行
            await asyncio.sleep(1)
        
        final_memory = memory_measurements[-1]
        max_memory = max(memory_measurements)
        memory_growth = final_memory - initial_memory
        
        self.logger.info(f"Memory Analysis:")
        self.logger.info(f"  Initial: {initial_memory:.2f}MB")
        self.logger.info(f"  Final: {final_memory:.2f}MB")
        self.logger.info(f"  Peak: {max_memory:.2f}MB")
        self.logger.info(f"  Growth: {memory_growth:.2f}MB")
        
        # 内存增长断言
        assert memory_growth <= 100, f"Memory growth too high: {memory_growth:.2f}MB"
        assert max_memory <= initial_memory + 200, f"Peak memory too high: {max_memory:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions_performance(self):
        """并发会话性能测试"""
        num_sessions = 50
        requests_per_session = 5
        
        async def session_conversation(session_id: str):
            """模拟一个会话的多轮对话"""
            session_results = []
            
            async with aiohttp.ClientSession() as http_session:
                for turn in range(requests_per_session):
                    start_time = time.time()
                    
                    chat_data = TestDataFactory.create_chat_request(
                        message=f"Session {session_id} turn {turn + 1}: Hello AI",
                        session_id=session_id
                    )
                    
                    try:
                        async with http_session.post(f"{self.base_url}/api/v1/chat", 
                                                   json=chat_data, timeout=30) as resp:
                            response_time = (time.time() - start_time) * 1000
                            
                            if resp.status == 200:
                                data = await resp.json()
                                session_results.append({
                                    "success": True,
                                    "response_time_ms": response_time,
                                    "turn": turn + 1,
                                    "session_id": session_id
                                })
                            else:
                                session_results.append({
                                    "success": False,
                                    "error": f"HTTP {resp.status}",
                                    "response_time_ms": response_time
                                })
                    except Exception as e:
                        response_time = (time.time() - start_time) * 1000
                        session_results.append({
                            "success": False,
                            "error": str(e),
                            "response_time_ms": response_time
                        })
                    
                    # 会话间稍作停顿
                    await asyncio.sleep(0.1)
            
            return session_results
        
        # 并发运行多个会话
        start_time = time.time()
        session_tasks = [
            session_conversation(f"concurrent-session-{i}")
            for i in range(num_sessions)
        ]
        
        session_results = await asyncio.gather(*session_tasks)
        test_duration = time.time() - start_time
        
        # 汇总所有请求结果
        all_results = []
        for session_result in session_results:
            all_results.extend(session_result)
        
        # 分析结果
        metrics = self.analyze_results("Concurrent Sessions", all_results, test_duration)
        self.report_metrics(metrics)
        
        # 并发会话性能断言
        assert metrics.error_rate <= 5.0, f"Error rate too high: {metrics.error_rate}%"
        assert metrics.avg_response_time <= 3000, f"Average response time too slow: {metrics.avg_response_time}ms"
        
        # 验证会话隔离
        successful_sessions = len([r for r in session_results if any(req["success"] for req in r)])
        session_success_rate = (successful_sessions / num_sessions) * 100
        assert session_success_rate >= 90, f"Session success rate too low: {session_success_rate}%"


@pytest.mark.performance
class TestPluginPerformance(PerformanceTestBase):
    """插件性能测试"""
    
    @pytest.mark.asyncio
    async def test_plugin_execution_performance(self):
        """插件执行性能测试"""
        async def execute_plugin():
            start_time = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    # 执行天气插件
                    plugin_data = {
                        "method": "get_current_weather",
                        "args": {"location": "Tokyo"}
                    }
                    
                    async with session.post(f"{self.base_url}/api/v1/plugins/weather/execute", 
                                          json=plugin_data, timeout=30) as resp:
                        response_time = (time.time() - start_time) * 1000
                        
                        if resp.status == 200:
                            data = await resp.json()
                            return {
                                "success": True,
                                "response_time_ms": response_time,
                                "execution_time": data.get("execution_time_ms", 0)
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {resp.status}",
                                "response_time_ms": response_time
                            }
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "error": str(e),
                    "response_time_ms": response_time
                }
        
        # 运行插件性能测试
        num_requests = 30
        concurrency = 10
        
        start_time = time.time()
        results = await self.run_concurrent_requests(
            execute_plugin, num_requests, concurrency
        )
        test_duration = time.time() - start_time
        
        # 分析结果
        metrics = self.analyze_results("Plugin Execution Performance", results, test_duration)
        self.report_metrics(metrics)
        
        # 插件性能断言
        assert metrics.error_rate <= 5.0, f"Plugin error rate too high: {metrics.error_rate}%"
        assert metrics.avg_response_time <= 1000, f"Plugin response time too slow: {metrics.avg_response_time}ms"


def generate_performance_report(test_results: List[PerformanceMetrics], output_file: str = "performance_report.json"):
    """生成性能测试报告"""
    report_data = {
        "test_timestamp": time.time(),
        "system_info": {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "platform": psutil.platform()
        },
        "test_results": []
    }
    
    for metrics in test_results:
        report_data["test_results"].append({
            "test_name": metrics.test_name,
            "metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "error_rate_percent": metrics.error_rate,
                "avg_response_time_ms": metrics.avg_response_time,
                "p95_response_time_ms": metrics.p95_response_time,
                "requests_per_second": metrics.requests_per_second,
                "memory_usage_mb": metrics.memory_usage_mb,
                "cpu_usage_percent": metrics.cpu_usage_percent,
                "test_duration_seconds": metrics.test_duration
            }
        })
    
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"Performance report generated: {output_file}")


# 用于在命令行运行性能测试的入口
if __name__ == "__main__":
    import sys
    
    # 简单的命令行界面
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Performance Test Runner")
        print("Usage: python test_performance.py [test_type]")
        print("  test_type: load, stress, memory, concurrency, plugin, all")
        sys.exit(0)
    
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    print(f"Running performance tests: {test_type}")
    
    # 这里可以添加实际的测试运行逻辑
    print("Use pytest to run performance tests:")
    print("  pytest tests/performance/ -v -m performance")
    print("  pytest tests/performance/ -v -k load")
    print("  pytest tests/performance/ -v -k stress")