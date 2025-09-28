#!/usr/bin/env python3
"""
对话系统功能测试套件
测试基础对话、复杂推理、上下文记忆、多轮对话、流式响应等功能
"""
import asyncio
import time
from typing import List, Dict, Any
from tests.base import BaseTestSuite, TestCase, TestResult, TestMetrics, PerformanceTestMixin


class DialogSystemTestSuite(BaseTestSuite, PerformanceTestMixin):
    """对话系统测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.dialog_test_cases = self._create_dialog_test_cases()
    
    def _create_dialog_test_cases(self) -> List[TestCase]:
        """创建对话测试用例"""
        return [
            # 基础对话测试
            TestCase(
                name="basic_greeting",
                description="测试基础问候对话",
                input_data={"message": "你好", "expected_model": "local", "max_time": 500},
                expected_output={"should_contain": ["你好", "助手"], "min_length": 10},
                category="基础对话",
                priority="HIGH"
            ),
            TestCase(
                name="self_introduction",
                description="测试自我介绍",
                input_data={"message": "你能做什么？", "expected_model": "auto", "max_time": 800},
                expected_output={"should_contain": ["助手", "帮助"], "min_length": 20},
                category="基础对话",
                priority="HIGH"
            ),
            TestCase(
                name="system_capabilities",
                description="测试系统能力介绍",
                input_data={"message": "介绍一下你自己", "expected_model": "auto", "max_time": 1000},
                expected_output={"should_contain": ["AI", "助手"], "min_length": 30},
                category="基础对话",
                priority="MEDIUM"
            ),
            
            # 复杂推理测试
            TestCase(
                name="complex_analysis",
                description="测试复杂分析任务",
                input_data={"message": "分析中美贸易战对全球经济的影响", "expected_model": "cloud", "max_time": 5000},
                expected_output={"should_contain": ["贸易", "经济", "影响"], "min_length": 100},
                category="复杂推理",
                priority="HIGH"
            ),
            TestCase(
                name="technical_design",
                description="测试技术设计任务",
                input_data={"message": "设计一个微服务架构方案", "expected_model": "cloud", "max_time": 8000},
                expected_output={"should_contain": ["微服务", "架构"], "min_length": 80},
                category="复杂推理",
                priority="MEDIUM"
            ),
            
            # 实时信息测试
            TestCase(
                name="weather_query",
                description="测试天气查询功能",
                input_data={"message": "今天北京天气怎么样？", "expected_plugin": "weather", "max_time": 3000},
                expected_output={"should_contain": ["天气", "北京"], "min_length": 20},
                category="实时信息",
                priority="HIGH"
            ),
            TestCase(
                name="current_tech_trends",
                description="测试最新技术趋势查询",
                input_data={"message": "最新的AI技术发展", "expected_model": "cloud", "max_time": 6000},
                expected_output={"should_contain": ["AI", "技术"], "min_length": 50},
                category="实时信息",
                priority="MEDIUM"
            ),
            
            # 上下文记忆测试
            TestCase(
                name="context_memory",
                description="测试上下文记忆",
                input_data={"message": "我刚才问了什么？", "requires_context": True, "max_time": 1000},
                expected_output={"should_reference_previous": True, "min_length": 15},
                category="上下文记忆",
                priority="HIGH"
            ),
            
            # 多轮对话测试
            TestCase(
                name="multi_turn_dialog",
                description="测试多轮对话连贯性",
                input_data={"turns": [
                    "我想学习Python编程",
                    "从哪里开始比较好？",
                    "需要什么基础知识？"
                ], "max_time": 2000},
                expected_output={"coherent": True, "contextual": True},
                category="多轮对话",
                priority="HIGH"
            ),
            
            # 流式响应测试
            TestCase(
                name="stream_response",
                description="测试流式响应",
                input_data={"message": "写一首关于春天的诗", "stream": True, "max_time": 5000},
                expected_output={"should_stream": True, "min_chunks": 3},
                category="流式响应",
                priority="MEDIUM"
            )
        ]
    
    async def run_test_case(self, test_case: TestCase):
        """运行单个对话测试用例"""
        try:
            if test_case.category == "基础对话":
                await self._test_basic_dialog(test_case)
            elif test_case.category == "复杂推理":
                await self._test_complex_reasoning(test_case)
            elif test_case.category == "实时信息":
                await self._test_realtime_info(test_case)
            elif test_case.category == "上下文记忆":
                await self._test_context_memory(test_case)
            elif test_case.category == "多轮对话":
                await self._test_multi_turn_dialog(test_case)
            elif test_case.category == "流式响应":
                await self._test_stream_response(test_case)
            else:
                self.record_test_result(test_case, TestResult.SKIP, 
                                      details={"error": f"未知测试类别: {test_case.category}"})
                
        except Exception as e:
            self.record_test_result(test_case, TestResult.ERROR,
                                  details={"error": f"测试执行异常: {str(e)}"})
    
    async def _test_basic_dialog(self, test_case: TestCase):
        """测试基础对话"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        # 发送请求
        result = await self.send_chat_request(message)
        
        # 检查响应
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        # 验证内容
        content = result.get("content", "")
        expected = test_case.expected_output
        
        # 检查必须包含的关键词
        missing_keywords = []
        for keyword in expected.get("should_contain", []):
            if keyword not in content:
                missing_keywords.append(keyword)
        
        # 检查最小长度
        min_length = expected.get("min_length", 0)
        if len(content) < min_length:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": f"回复长度不足: {len(content)} < {min_length}"})
            return
        
        if missing_keywords:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": f"缺少关键词: {missing_keywords}"})
            return
        
        # 检查响应时间
        response_time = result.get("_response_time_ms", 0)
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        # 记录成功结果
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=result.get("model_used", "unknown"),
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=True
        )
        
        self.record_test_result(test_case, TestResult.PASS, metrics=metrics,
                              details={"content_length": len(content), "performance_ok": performance_ok})
    
    async def _test_complex_reasoning(self, test_case: TestCase):
        """测试复杂推理"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_chat_request(message, max_tokens=2000)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        expected = test_case.expected_output
        
        # 验证复杂推理内容质量
        missing_keywords = []
        for keyword in expected.get("should_contain", []):
            if keyword not in content:
                missing_keywords.append(keyword)
        
        min_length = expected.get("min_length", 0)
        if len(content) < min_length:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": f"推理内容长度不足: {len(content)} < {min_length}"})
            return
        
        if missing_keywords:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": f"推理内容缺少关键概念: {missing_keywords}"})
            return
        
        # 检查是否使用了合适的模型
        model_used = result.get("model_used", "")
        expected_model = test_case.input_data.get("expected_model")
        if expected_model == "cloud" and "cloud" not in model_used.lower():
            self.logger.warning(f"预期使用云端模型，实际使用: {model_used}")
        
        response_time = result.get("_response_time_ms", 0)
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=model_used,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=True
        )
        
        self.record_test_result(test_case, TestResult.PASS, metrics=metrics,
                              details={"reasoning_quality": "satisfactory", "performance_ok": performance_ok})
    
    async def _test_realtime_info(self, test_case: TestCase):
        """测试实时信息查询"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        expected = test_case.expected_output
        
        # 验证实时信息内容
        missing_keywords = []
        for keyword in expected.get("should_contain", []):
            if keyword not in content:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": f"实时信息缺少关键词: {missing_keywords}"})
            return
        
        # 检查是否调用了插件
        expected_plugin = test_case.input_data.get("expected_plugin")
        if expected_plugin:
            # 这里可以检查日志或响应元数据来确认插件使用
            self.logger.info(f"预期使用插件: {expected_plugin}")
        
        response_time = result.get("_response_time_ms", 0)
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=result.get("model_used", "unknown"),
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=True
        )
        
        self.record_test_result(test_case, TestResult.PASS, metrics=metrics,
                              details={"info_type": "realtime", "performance_ok": performance_ok})
    
    async def _test_context_memory(self, test_case: TestCase):
        """测试上下文记忆"""
        # 首先发送一个问题来建立上下文
        context_message = "我想了解机器学习的基础知识"
        await self.send_chat_request(context_message)
        
        # 等待一下确保上下文被保存
        await asyncio.sleep(1)
        
        # 然后发送需要上下文的问题
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_chat_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        
        # 检查是否引用了之前的上下文
        context_indicators = ["刚才", "之前", "上面", "机器学习", "刚刚"]
        has_context_reference = any(indicator in content for indicator in context_indicators)
        
        if not has_context_reference:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": "未能正确引用上下文"})
            return
        
        response_time = result.get("_response_time_ms", 0)
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=result.get("model_used", "unknown"),
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=True
        )
        
        self.record_test_result(test_case, TestResult.PASS, metrics=metrics,
                              details={"context_referenced": True, "performance_ok": performance_ok})
    
    async def _test_multi_turn_dialog(self, test_case: TestCase):
        """测试多轮对话"""
        turns = test_case.input_data["turns"]
        max_time = test_case.input_data["max_time"]
        
        responses = []
        total_time = 0
        
        for i, turn in enumerate(turns, 1):
            result = await self.send_chat_request(turn)
            
            if "error" in result:
                self.record_test_result(test_case, TestResult.FAIL,
                                      details={"error": f"第{i}轮对话失败: {result['error']}"})
                return
            
            responses.append(result.get("content", ""))
            total_time += result.get("_response_time_ms", 0)
            
            # 轮次间隔
            await asyncio.sleep(0.5)
        
        # 检查对话连贯性
        coherent = True
        for i in range(1, len(responses)):
            # 简单检查：后续回复应该与主题相关
            if "Python" in turns[0] and "Python" not in responses[i]:
                coherent = False
                break
        
        performance_ok = self.assert_performance(total_time, max_time * len(turns), test_case.name)
        
        if not coherent:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": "多轮对话缺乏连贯性"})
            return
        
        metrics = TestMetrics(
            response_time_ms=int(total_time / len(turns)),  # 平均响应时间
            token_count=sum(len(r.split()) for r in responses),
            model_used="multi-turn",
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=True
        )
        
        self.record_test_result(test_case, TestResult.PASS, metrics=metrics,
                              details={"turns": len(turns), "coherent": coherent, "performance_ok": performance_ok})
    
    async def _test_stream_response(self, test_case: TestCase):
        """测试流式响应"""
        message = test_case.input_data["message"]
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_stream_request(message)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        chunk_count = result.get("chunk_count", 0)
        min_chunks = test_case.expected_output.get("min_chunks", 1)
        
        if chunk_count < min_chunks:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": f"流式块数不足: {chunk_count} < {min_chunks}"})
            return
        
        response_time = result.get("_response_time_ms", 0)
        performance_ok = self.assert_performance(response_time, max_time, test_case.name)
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=len(result.get("content", "").split()),
            model_used="stream",
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=True
        )
        
        self.record_test_result(test_case, TestResult.PASS, metrics=metrics,
                              details={"chunks": chunk_count, "stream_ok": True, "performance_ok": performance_ok})
    
    async def run_dialog_tests(self):
        """运行所有对话测试"""
        self.logger.info("🗣️ 开始对话系统功能测试")
        await self.run_all_tests(self.dialog_test_cases)


async def main():
    """主函数"""
    test_suite = DialogSystemTestSuite()
    
    try:
        await test_suite.run_dialog_tests()
    except KeyboardInterrupt:
        test_suite.logger.info("测试被用户中断")
    except Exception as e:
        test_suite.logger.error(f"测试运行异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())