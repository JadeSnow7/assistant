#!/usr/bin/env python3
"""
资源管理功能测试套件 - 第一部分
测试系统监控、性能优化、资源分配等功能
"""
import asyncio
import time
import psutil
import json
from typing import List, Dict, Any, Optional
from tests.base import BaseTestSuite, TestCase, TestResult, TestMetrics, PerformanceTestMixin


class ResourceManagementTestSuite(BaseTestSuite, PerformanceTestMixin):
    """资源管理测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.resource_test_cases = self._create_resource_test_cases()
        self.baseline_metrics = {}
    
    def _create_resource_test_cases(self) -> List[TestCase]:
        """创建资源管理测试用例"""
        return [
            # 系统资源监控测试
            TestCase(
                name="cpu_monitoring_accuracy",
                description="CPU使用率监控精度测试",
                input_data={
                    "message": "显示CPU使用率详细信息",
                    "resource_type": "cpu",
                    "accuracy_threshold": 5.0,
                    "max_time": 2000
                },
                expected_output={"should_contain": ["CPU", "使用率", "%"], "accuracy_requirement": True},
                category="系统监控",
                priority="HIGH"
            ),
            TestCase(
                name="memory_monitoring_accuracy", 
                description="内存使用率监控精度测试",
                input_data={
                    "message": "查看内存使用详情",
                    "resource_type": "memory",
                    "accuracy_threshold": 2.0,
                    "max_time": 2000
                },
                expected_output={"should_contain": ["内存", "使用", "MB"], "accuracy_requirement": True},
                category="系统监控",
                priority="HIGH"
            ),
            # 资源管理决策测试
            TestCase(
                name="high_cpu_load_response",
                description="高CPU负载响应测试",
                input_data={
                    "message": "系统CPU使用率很高，怎么办？",
                    "simulate_condition": {"cpu_usage": 85},
                    "expected_action": "route_to_cloud",
                    "max_time": 3000
                },
                expected_output={"should_suggest_optimization": True, "load_balancing": True},
                category="资源管理决策",
                priority="HIGH"
            ),
            # 性能优化测试
            TestCase(
                name="concurrent_request_handling",
                description="并发请求处理优化测试",
                input_data={
                    "concurrent_requests": 3,
                    "request_type": "mixed_complexity",
                    "max_time": 6000
                },
                expected_output={"all_requests_handled": True, "no_resource_exhaustion": True},
                category="性能优化",
                priority="HIGH"
            )
        ]
    
    async def setup(self):
        """测试套件初始化"""
        await super().setup()
        self.baseline_metrics = await self._get_system_baseline()
        self.logger.info(f"📊 基线系统指标: {self.baseline_metrics}")
    
    async def _get_system_baseline(self) -> Dict[str, float]:
        """获取系统基线指标"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent
            }
        except Exception as e:
            self.logger.warning(f"获取系统基线失败: {e}")
            return {}
    
    async def run_test_case(self, test_case: TestCase):
        """运行单个资源管理测试用例"""
        try:
            if test_case.category == "系统监控":
                await self._test_system_monitoring(test_case)
            elif test_case.category == "资源管理决策":
                await self._test_resource_management_decision(test_case)
            elif test_case.category == "性能优化":
                await self._test_performance_optimization(test_case)
            else:
                self.record_test_result(test_case, TestResult.SKIP,
                                      details={"error": f"未知资源测试类别: {test_case.category}"})
        except Exception as e:
            self.record_test_result(test_case, TestResult.ERROR,
                                  details={"error": f"资源管理测试执行异常: {str(e)}"})
    
    async def _test_system_monitoring(self, test_case: TestCase):
        """测试系统监控功能"""
        message = test_case.input_data["message"]
        resource_type = test_case.input_data["resource_type"]
        max_time = test_case.input_data["max_time"]
        
        actual_metrics = await self._get_actual_system_metrics(resource_type)
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL, details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        response_time = result.get("_response_time_ms", 0)
        
        # 检查必要信息包含
        expected = test_case.expected_output
        missing_keywords = []
        for keyword in expected.get("should_contain", []):
            if keyword not in content:
                missing_keywords.append(keyword)
        
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        success = len(missing_keywords) == 0 and performance_ok
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=result.get("model_used", ""),
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=success
        )
        
        test_result = TestResult.PASS if success else TestResult.FAIL
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={"missing_keywords": missing_keywords, "performance_ok": performance_ok})
    
    async def _get_actual_system_metrics(self, resource_type: str) -> Dict[str, float]:
        """获取实际系统指标"""
        try:
            if resource_type == "cpu":
                return {"cpu_percent": psutil.cpu_percent(interval=1)}
            elif resource_type == "memory":
                mem = psutil.virtual_memory()
                return {"memory_percent": mem.percent, "memory_used_gb": mem.used / (1024**3)}
            else:
                return {}
        except Exception as e:
            self.logger.warning(f"获取{resource_type}指标失败: {e}")
            return {}
    
    async def _test_resource_management_decision(self, test_case: TestCase):
        """测试资源管理决策"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL, details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        response_time = result.get("_response_time_ms", 0)
        
        # 检查决策建议
        expected = test_case.expected_output
        decision_checks = {}
        
        if expected.get("should_suggest_optimization", False):
            optimization_keywords = ["优化", "改善", "提升", "减少", "降低"]
            decision_checks["suggests_optimization"] = any(kw in content for kw in optimization_keywords)
        
        if expected.get("load_balancing", False):
            balance_keywords = ["均衡", "分配", "负载", "平衡"]
            decision_checks["load_balancing"] = any(kw in content for kw in balance_keywords)
        
        decision_quality = sum(1 for v in decision_checks.values() if v is True) / len(decision_checks) if decision_checks else 0
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        success = decision_quality >= 0.7 and performance_ok
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=result.get("model_used", ""),
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=success
        )
        
        test_result = TestResult.PASS if success else TestResult.FAIL
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={"decision_checks": decision_checks, "decision_quality": decision_quality})
    
    async def _test_performance_optimization(self, test_case: TestCase):
        """测试性能优化功能"""
        if "concurrent_requests" in test_case.input_data:
            await self._test_concurrent_handling(test_case)
        else:
            # 单个优化测试的简化版本
            message = test_case.input_data.get("message", "优化系统性能")
            max_time = test_case.input_data["max_time"]
            
            result = await self.send_chat_request(message)
            
            if "error" in result:
                self.record_test_result(test_case, TestResult.FAIL, details={"error": result["error"]})
                return
            
            response_time = result.get("_response_time_ms", 0)
            performance_ok = self.assert_performance(response_time, max_time, test_case.name)
            
            metrics = TestMetrics(
                response_time_ms=response_time,
                token_count=result.get("token_count", 0),
                model_used=result.get("model_used", ""),
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                success=performance_ok
            )
            
            test_result = TestResult.PASS if performance_ok else TestResult.FAIL
            self.record_test_result(test_case, test_result, metrics=metrics)
    
    async def _test_concurrent_handling(self, test_case: TestCase):
        """测试并发请求处理"""
        concurrent_requests = test_case.input_data["concurrent_requests"]
        max_time = test_case.input_data["max_time"]
        
        # 创建简单测试请求
        test_messages = ["简单问题1", "简单问题2", "简单问题3"][:concurrent_requests]
        
        start_time = time.time()
        
        # 并发发送请求
        tasks = [asyncio.create_task(self.send_chat_request(msg)) for msg in test_messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = int((time.time() - start_time) * 1000)
        
        # 分析结果
        successful_requests = [r for r in results if isinstance(r, dict) and "error" not in r]
        failed_requests = len(results) - len(successful_requests)
        
        concurrent_analysis = {
            "all_requests_handled": len(successful_requests) == concurrent_requests,
            "no_failures": failed_requests == 0,
            "reasonable_time": total_time <= max_time
        }
        
        success = all(concurrent_analysis.values())
        
        avg_response_time = sum(r.get("_response_time_ms", 0) for r in successful_requests) / len(successful_requests) if successful_requests else 0
        
        metrics = TestMetrics(
            response_time_ms=int(avg_response_time),
            token_count=sum(r.get("token_count", 0) for r in successful_requests),
            model_used="concurrent",
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=success
        )
        
        test_result = TestResult.PASS if success else TestResult.FAIL
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={"concurrent_analysis": concurrent_analysis, "total_time": total_time})
    
    async def run_resource_tests(self):
        """运行所有资源管理测试"""
        self.logger.info("🔧 开始资源管理功能测试")
        await self.run_all_tests(self.resource_test_cases)


async def main():
    """主函数"""
    test_suite = ResourceManagementTestSuite()
    
    try:
        await test_suite.run_resource_tests()
    except KeyboardInterrupt:
        test_suite.logger.info("测试被用户中断")
    except Exception as e:
        test_suite.logger.error(f"资源管理测试运行异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())