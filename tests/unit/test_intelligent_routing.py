#!/usr/bin/env python3
"""
智能路由决策验证测试套件
测试本地/云端模型选择逻辑，验证AI任务动态路由策略
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from tests.unit.base import BaseTestSuite, TestCase, TestResult, TestMetrics, PerformanceTestMixin


class IntelligentRoutingTestSuite(BaseTestSuite, PerformanceTestMixin):
    """智能路由决策测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.routing_test_cases = self._create_routing_test_cases()
    
    def _create_routing_test_cases(self) -> List[TestCase]:
        """创建路由决策测试用例"""
        return [
            # 简单任务 - 应该使用本地模型
            TestCase(
                name="simple_greeting_routing",
                description="简单问候应该路由到本地模型",
                input_data={
                    "message": "你好",
                    "expected_route": "local",
                    "complexity": "simple",
                    "max_time": 1000
                },
                expected_output={"model_type": "local", "fast_response": True},
                category="简单任务路由",
                priority="HIGH"
            ),
            TestCase(
                name="basic_qa_routing",
                description="基础问答应该路由到本地模型",
                input_data={
                    "message": "什么是Python？",
                    "expected_route": "local",
                    "complexity": "simple",
                    "max_time": 1500
                },
                expected_output={"model_type": "local", "accurate_response": True},
                category="简单任务路由",
                priority="HIGH"
            ),
            TestCase(
                name="simple_calculation",
                description="简单计算应该路由到本地模型",
                input_data={
                    "message": "1+1等于多少？",
                    "expected_route": "local", 
                    "complexity": "simple",
                    "max_time": 800
                },
                expected_output={"model_type": "local", "correct_answer": True},
                category="简单任务路由",
                priority="MEDIUM"
            ),
            
            # 复杂任务 - 应该使用云端模型
            TestCase(
                name="complex_analysis_routing",
                description="复杂分析应该路由到云端模型",
                input_data={
                    "message": "分析人工智能对未来劳动力市场的深层影响，包括技术发展趋势、政策建议和社会适应策略",
                    "expected_route": "cloud",
                    "complexity": "complex",
                    "max_time": 10000
                },
                expected_output={"model_type": "cloud", "comprehensive_analysis": True},
                category="复杂任务路由",
                priority="HIGH"
            ),
            TestCase(
                name="creative_writing_routing",
                description="创意写作应该路由到云端模型",
                input_data={
                    "message": "写一个关于时间旅行的科幻小说开头，要求情节新颖，人物生动，语言优美",
                    "expected_route": "cloud",
                    "complexity": "complex",
                    "max_time": 15000
                },
                expected_output={"model_type": "cloud", "creative_content": True},
                category="复杂任务路由",
                priority="MEDIUM"
            ),
            TestCase(
                name="technical_architecture_routing",
                description="技术架构设计应该路由到云端模型",
                input_data={
                    "message": "设计一个支持千万级用户的分布式社交媒体系统架构，包括数据库设计、缓存策略、负载均衡和安全考虑",
                    "expected_route": "cloud",
                    "complexity": "complex",
                    "max_time": 12000
                },
                expected_output={"model_type": "cloud", "detailed_design": True},
                category="复杂任务路由",
                priority="HIGH"
            ),
            
            # 中等复杂度任务 - 智能路由
            TestCase(
                name="code_review_routing",
                description="代码审查任务的智能路由",
                input_data={
                    "message": "请审查这段Python代码并提出改进建议：def add(a, b): return a + b",
                    "expected_route": "auto",
                    "complexity": "medium",
                    "max_time": 3000
                },
                expected_output={"appropriate_route": True, "quality_feedback": True},
                category="智能路由",
                priority="MEDIUM"
            ),
            TestCase(
                name="explanation_routing",
                description="技术概念解释的智能路由",
                input_data={
                    "message": "解释一下什么是微服务架构，包括优缺点",
                    "expected_route": "auto",
                    "complexity": "medium",
                    "max_time": 4000
                },
                expected_output={"appropriate_route": True, "comprehensive_explanation": True},
                category="智能路由",
                priority="MEDIUM"
            ),
            
            # 插件路由测试
            TestCase(
                name="weather_plugin_routing",
                description="天气查询应该路由到天气插件",
                input_data={
                    "message": "上海明天天气怎么样？",
                    "expected_route": "plugin",
                    "expected_plugin": "weather",
                    "max_time": 5000
                },
                expected_output={"plugin_used": True, "weather_data": True},
                category="插件路由",
                priority="HIGH"
            ),
            TestCase(
                name="system_command_routing",
                description="系统命令应该路由到系统插件",
                input_data={
                    "message": "查看当前系统CPU使用情况",
                    "expected_route": "plugin", 
                    "expected_plugin": "system",
                    "max_time": 3000
                },
                expected_output={"plugin_used": True, "system_info": True},
                category="插件路由",
                priority="MEDIUM"
            ),
            
            # 负载均衡测试
            TestCase(
                name="load_balance_routing",
                description="高负载时的负载均衡路由",
                input_data={
                    "message": "解释量子计算的基本原理",
                    "expected_route": "auto",
                    "simulate_high_load": True,
                    "max_time": 8000
                },
                expected_output={"load_balanced": True, "reasonable_response_time": True},
                category="负载均衡",
                priority="MEDIUM"
            ),
            
            # 资源限制测试
            TestCase(
                name="resource_constraint_routing",
                description="资源受限时的路由决策",
                input_data={
                    "message": "帮我写一个复杂的算法实现",
                    "expected_route": "auto",
                    "simulate_resource_constraint": True,
                    "max_time": 6000
                },
                expected_output={"resource_aware": True, "alternative_route": True},
                category="资源约束",
                priority="MEDIUM"
            )
        ]
    
    async def run_test_case(self, test_case: TestCase):
        """运行单个路由测试用例"""
        try:
            if test_case.category in ["简单任务路由", "复杂任务路由"]:
                await self._test_complexity_based_routing(test_case)
            elif test_case.category == "智能路由":
                await self._test_intelligent_routing(test_case)
            elif test_case.category == "插件路由":
                await self._test_plugin_routing(test_case)
            elif test_case.category == "负载均衡":
                await self._test_load_balance_routing(test_case)
            elif test_case.category == "资源约束":
                await self._test_resource_constraint_routing(test_case)
            else:
                self.record_test_result(test_case, TestResult.SKIP,
                                      details={"error": f"未知路由测试类别: {test_case.category}"})
                
        except Exception as e:
            self.record_test_result(test_case, TestResult.ERROR,
                                  details={"error": f"路由测试执行异常: {str(e)}"})
    
    async def _test_complexity_based_routing(self, test_case: TestCase):
        """测试基于复杂度的路由决策"""
        message = test_case.input_data["message"]
        expected_route = test_case.input_data["expected_route"]
        complexity = test_case.input_data["complexity"]
        max_time = test_case.input_data["max_time"]
        
        # 发送请求
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        # 分析路由决策
        model_used = result.get("model_used", "").lower()
        reasoning = result.get("reasoning", "").lower()
        response_time = result.get("_response_time_ms", 0)
        
        # 验证路由决策
        route_correct = False
        
        if expected_route == "local":
            # 简单任务应该使用本地模型
            route_correct = any(indicator in model_used for indicator in ["local", "qwen", "ollama"])
            if not route_correct:
                # 检查推理过程中的路由原因
                route_correct = any(indicator in reasoning for indicator in ["本地", "简单", "快速"])
        
        elif expected_route == "cloud":
            # 复杂任务应该使用云端模型
            route_correct = any(indicator in model_used for indicator in ["cloud", "gemini", "gpt"])
            if not route_correct:
                route_correct = any(indicator in reasoning for indicator in ["云端", "复杂", "详细"])
        
        if not route_correct:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={
                                      "error": f"路由决策错误: 期望{expected_route}, 实际使用{model_used}",
                                      "reasoning": reasoning
                                  })
            return
        
        # 验证响应质量
        content = result.get("content", "")
        quality_ok = True
        
        if complexity == "simple":
            # 简单任务应该快速响应
            if response_time > max_time:
                quality_ok = False
                self.logger.warning(f"简单任务响应时间过长: {response_time}ms > {max_time}ms")
        
        elif complexity == "complex":
            # 复杂任务应该有详细回答
            if len(content) < 100:
                quality_ok = False
                self.logger.warning(f"复杂任务回答过于简短: {len(content)} chars")
        
        # 记录结果
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=model_used,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=route_correct and quality_ok
        )
        
        test_result = TestResult.PASS if (route_correct and quality_ok) else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "route_correct": route_correct,
                                  "quality_ok": quality_ok,
                                  "performance_ok": performance_ok,
                                  "complexity": complexity,
                                  "actual_model": model_used
                              })
    
    async def _test_intelligent_routing(self, test_case: TestCase):
        """测试智能路由决策"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        model_used = result.get("model_used", "")
        reasoning = result.get("reasoning", "")
        content = result.get("content", "")
        response_time = result.get("_response_time_ms", 0)
        
        # 智能路由评估标准
        route_appropriate = True
        quality_assessment = {}
        
        # 检查路由合理性
        if "代码" in message or "code" in message.lower():
            # 代码相关任务，检查回答质量
            if len(content) < 50:
                route_appropriate = False
                quality_assessment["code_quality"] = "insufficient"
            else:
                quality_assessment["code_quality"] = "adequate"
        
        elif "解释" in message or "explain" in message.lower():
            # 解释任务，检查解释的完整性
            if len(content) < 80:
                route_appropriate = False
                quality_assessment["explanation_quality"] = "insufficient"
            else:
                quality_assessment["explanation_quality"] = "comprehensive"
        
        # 检查决策推理
        has_reasoning = len(reasoning) > 10
        quality_assessment["has_reasoning"] = has_reasoning
        
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=model_used,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=route_appropriate
        )
        
        test_result = TestResult.PASS if route_appropriate else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "route_appropriate": route_appropriate,
                                  "quality_assessment": quality_assessment,
                                  "performance_ok": performance_ok,
                                  "reasoning_provided": has_reasoning
                              })
    
    async def _test_plugin_routing(self, test_case: TestCase):
        """测试插件路由"""
        message = test_case.input_data["message"]
        expected_plugin = test_case.input_data.get("expected_plugin")
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        model_used = result.get("model_used", "")
        reasoning = result.get("reasoning", "")
        response_time = result.get("_response_time_ms", 0)
        
        # 检查是否使用了插件
        plugin_used = False
        plugin_indicators = ["plugin", "插件", "调用", "查询"]
        
        if any(indicator in reasoning.lower() for indicator in plugin_indicators):
            plugin_used = True
        
        # 针对特定插件的验证
        plugin_result_valid = False
        
        if expected_plugin == "weather":
            # 天气插件应该返回天气相关信息
            weather_keywords = ["天气", "温度", "湿度", "风", "晴", "雨", "云"]
            plugin_result_valid = any(keyword in content for keyword in weather_keywords)
        
        elif expected_plugin == "system":
            # 系统插件应该返回系统信息
            system_keywords = ["CPU", "内存", "磁盘", "进程", "%"]
            plugin_result_valid = any(keyword in content for keyword in system_keywords)
        
        else:
            # 通用插件验证
            plugin_result_valid = len(content) > 20
        
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        success = plugin_used and plugin_result_valid
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=model_used,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=success
        )
        
        test_result = TestResult.PASS if success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "plugin_used": plugin_used,
                                  "plugin_result_valid": plugin_result_valid,
                                  "expected_plugin": expected_plugin,
                                  "performance_ok": performance_ok
                              })
    
    async def _test_load_balance_routing(self, test_case: TestCase):
        """测试负载均衡路由"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        simulate_high_load = test_case.input_data.get("simulate_high_load", False)
        
        if simulate_high_load:
            # 模拟高负载：同时发送多个请求
            tasks = []
            for i in range(3):
                task = asyncio.create_task(self.send_chat_request(f"{message} (请求{i+1})"))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 分析负载均衡效果
            successful_requests = [r for r in results if isinstance(r, dict) and "error" not in r]
            failed_requests = [r for r in results if isinstance(r, Exception) or (isinstance(r, dict) and "error" in r)]
            
            if len(successful_requests) < 2:
                self.record_test_result(test_case, TestResult.FAIL,
                                      details={"error": f"高负载下成功请求过少: {len(successful_requests)}/3"})
                return
            
            # 检查响应时间分布
            response_times = [r.get("_response_time_ms", 0) for r in successful_requests]
            avg_response_time = sum(response_times) / len(response_times)
            
            load_balanced = avg_response_time <= max_time
            
            metrics = TestMetrics(
                response_time_ms=int(avg_response_time),
                token_count=sum(r.get("token_count", 0) for r in successful_requests),
                model_used="load_balanced",
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                success=load_balanced
            )
            
            test_result = TestResult.PASS if load_balanced else TestResult.FAIL
            
            self.record_test_result(test_case, test_result, metrics=metrics,
                                  details={
                                      "successful_requests": len(successful_requests),
                                      "failed_requests": len(failed_requests),
                                      "avg_response_time": avg_response_time,
                                      "load_balanced": load_balanced
                                  })
        
        else:
            # 普通负载均衡测试
            result = await self.send_chat_request(message)
            
            if "error" in result:
                self.record_test_result(test_case, TestResult.FAIL,
                                      details={"error": result["error"]})
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
            
            self.record_test_result(test_case, test_result, metrics=metrics,
                                  details={"performance_ok": performance_ok})
    
    async def _test_resource_constraint_routing(self, test_case: TestCase):
        """测试资源约束下的路由决策"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        # 获取系统状态
        system_status = await self.get_system_status()
        
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        model_used = result.get("model_used", "")
        reasoning = result.get("reasoning", "")
        response_time = result.get("_response_time_ms", 0)
        
        # 检查是否考虑了资源约束
        resource_aware = False
        if "资源" in reasoning or "负载" in reasoning or "性能" in reasoning:
            resource_aware = True
        
        # 在资源受限情况下，应该选择更高效的路由
        efficient_route = True
        if response_time > max_time * 1.5:  # 允许一定的时间延长
            efficient_route = False
        
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        success = resource_aware and efficient_route
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=model_used,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=success
        )
        
        test_result = TestResult.PASS if success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "resource_aware": resource_aware,
                                  "efficient_route": efficient_route,
                                  "performance_ok": performance_ok,
                                  "system_status": system_status
                              })
    
    async def run_routing_tests(self):
        """运行所有路由决策测试"""
        self.logger.info("🧭 开始智能路由决策验证测试")
        await self.run_all_tests(self.routing_test_cases)


async def main():
    """主函数"""
    test_suite = IntelligentRoutingTestSuite()
    
    try:
        await test_suite.run_routing_tests()
    except KeyboardInterrupt:
        test_suite.logger.info("测试被用户中断")
    except Exception as e:
        test_suite.logger.error(f"路由测试运行异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())