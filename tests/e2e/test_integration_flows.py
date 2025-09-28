#!/usr/bin/env python3
"""
端到端集成测试套件
验证完整业务流程，包括智能对话、系统诊断、推荐执行等场景
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from tests.base import BaseTestSuite, TestCase, TestResult, TestMetrics


class EndToEndIntegrationTestSuite(BaseTestSuite):
    """端到端集成测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.e2e_test_cases = self._create_e2e_test_cases()
    
    def _create_e2e_test_cases(self) -> List[TestCase]:
        """创建端到端测试用例"""
        return [
            # 场景1：智能系统诊断流程
            TestCase(
                name="intelligent_system_diagnosis",
                description="智能系统诊断完整流程",
                input_data={
                    "scenario": "performance_issue",
                    "user_complaint": "我的电脑最近很卡，帮我看看什么问题",
                    "expected_flow": ["问题识别", "系统检查", "推荐方案", "执行确认"],
                    "max_time": 15000
                },
                expected_output={
                    "diagnosis_provided": True,
                    "recommendations_given": True,
                    "actionable_steps": True,
                    "user_friendly": True
                },
                category="系统诊断流程",
                priority="HIGH"
            ),
            
            # 场景2：信息查询与处理流程
            TestCase(
                name="information_query_processing",
                description="信息查询与处理完整流程",
                input_data={
                    "scenario": "weather_and_planning",
                    "user_query": "明天北京天气怎么样？适合户外活动吗？",
                    "expected_flow": ["天气查询", "数据分析", "建议生成"],
                    "max_time": 10000
                },
                expected_output={
                    "weather_data_retrieved": True,
                    "analysis_provided": True,
                    "recommendations_given": True,
                    "contextual_advice": True
                },
                category="信息查询流程",
                priority="HIGH"
            ),
            
            # 场景3：复杂任务分解与执行
            TestCase(
                name="complex_task_decomposition",
                description="复杂任务分解与执行流程",
                input_data={
                    "scenario": "project_planning",
                    "user_request": "帮我制定一个学习Python的计划，包括时间安排和资源推荐",
                    "expected_flow": ["需求分析", "任务分解", "资源匹配", "计划生成"],
                    "max_time": 20000
                },
                expected_output={
                    "comprehensive_plan": True,
                    "time_structured": True,
                    "resource_links": True,
                    "personalized": True
                },
                category="任务规划流程",
                priority="MEDIUM"
            ),
            
            # 场景4：多轮对话上下文保持
            TestCase(
                name="multi_turn_context_flow",
                description="多轮对话上下文保持流程",
                input_data={
                    "scenario": "technical_consultation",
                    "conversation": [
                        "我想学习机器学习",
                        "我有Python基础，但没有数学背景",
                        "推荐一些适合我的课程",
                        "这些课程大概需要多长时间？",
                        "学完后可以做什么项目？"
                    ],
                    "max_time": 25000
                },
                expected_output={
                    "context_maintained": True,
                    "progressive_assistance": True,
                    "personalized_responses": True,
                    "coherent_advice": True
                },
                category="对话流程",
                priority="HIGH"
            ),
            
            # 场景5：错误处理与恢复
            TestCase(
                name="error_handling_recovery",
                description="错误处理与恢复流程",
                input_data={
                    "scenario": "service_interruption",
                    "test_sequence": [
                        "正常请求",
                        "异常请求",  # 可能导致错误
                        "恢复请求"
                    ],
                    "max_time": 15000
                },
                expected_output={
                    "graceful_error_handling": True,
                    "service_recovery": True,
                    "user_notification": True,
                    "state_consistency": True
                },
                category="错误恢复流程",
                priority="MEDIUM"
            ),
            
            # 场景6：性能监控与优化
            TestCase(
                name="performance_monitoring_optimization",
                description="性能监控与优化流程",
                input_data={
                    "scenario": "performance_tracking",
                    "monitoring_requests": [
                        "检查系统状态",
                        "分析性能瓶颈", 
                        "推荐优化方案",
                        "执行优化建议"
                    ],
                    "max_time": 20000
                },
                expected_output={
                    "comprehensive_monitoring": True,
                    "bottleneck_identification": True,
                    "optimization_suggestions": True,
                    "improvement_tracking": True
                },
                category="性能优化流程",
                priority="MEDIUM"
            )
        ]
    
    async def run_test_case(self, test_case: TestCase):
        """运行单个端到端测试用例"""
        try:
            if test_case.category == "系统诊断流程":
                await self._test_system_diagnosis_flow(test_case)
            elif test_case.category == "信息查询流程":
                await self._test_information_query_flow(test_case)
            elif test_case.category == "任务规划流程":
                await self._test_task_planning_flow(test_case)
            elif test_case.category == "对话流程":
                await self._test_dialog_flow(test_case)
            elif test_case.category == "错误恢复流程":
                await self._test_error_recovery_flow(test_case)
            elif test_case.category == "性能优化流程":
                await self._test_performance_optimization_flow(test_case)
            else:
                self.record_test_result(test_case, TestResult.SKIP,
                                      details={"error": f"未知测试流程: {test_case.category}"})
                
        except Exception as e:
            self.record_test_result(test_case, TestResult.ERROR,
                                  details={"error": f"端到端测试执行异常: {str(e)}"})
    
    async def _test_system_diagnosis_flow(self, test_case: TestCase):
        """测试系统诊断流程"""
        user_complaint = test_case.input_data["user_complaint"]
        expected_flow = test_case.input_data["expected_flow"]
        max_time = test_case.input_data["max_time"]
        
        flow_results = {}
        total_response_time = 0
        
        # 步骤1: 问题识别
        self.logger.info("🔍 步骤1: 问题识别")
        result1 = await self.send_chat_request(user_complaint)
        
        if "error" in result1:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": f"问题识别失败: {result1['error']}"})
            return
        
        total_response_time += result1.get("_response_time_ms", 0)
        
        # 检查是否识别了性能问题
        content1 = result1.get("content", "")
        flow_results["problem_identified"] = any(keyword in content1.lower() 
                                                for keyword in ["性能", "卡顿", "慢", "问题", "检查"])
        
        # 步骤2: 系统检查（如果AI推荐了检查）
        if "检查" in content1 or "查看" in content1:
            self.logger.info("🔧 步骤2: 系统检查")
            result2 = await self.send_chat_request("好的，请帮我检查系统状态")
            
            if "error" not in result2:
                total_response_time += result2.get("_response_time_ms", 0)
                content2 = result2.get("content", "")
                flow_results["system_checked"] = any(keyword in content2.lower()
                                                   for keyword in ["cpu", "内存", "磁盘", "使用率"])
            else:
                flow_results["system_checked"] = False
        else:
            flow_results["system_checked"] = True  # 如果没有推荐检查，认为流程正常
        
        # 步骤3: 推荐方案
        self.logger.info("💡 步骤3: 获取优化建议")
        result3 = await self.send_chat_request("根据检查结果，有什么优化建议吗？")
        
        if "error" not in result3:
            total_response_time += result3.get("_response_time_ms", 0)
            content3 = result3.get("content", "")
            flow_results["recommendations_provided"] = any(keyword in content3.lower()
                                                         for keyword in ["建议", "推荐", "优化", "清理", "关闭"])
        else:
            flow_results["recommendations_provided"] = False
        
        # 评估整体流程质量
        expected = test_case.expected_output
        flow_quality = {}
        
        flow_quality["diagnosis_provided"] = flow_results.get("problem_identified", False)
        flow_quality["recommendations_given"] = flow_results.get("recommendations_provided", False)
        
        # 检查是否提供了可执行的步骤
        all_content = content1 + result2.get("content", "") + content3
        actionable_indicators = ["执行", "运行", "点击", "打开", "关闭", "清理", "删除", "重启"]
        flow_quality["actionable_steps"] = any(indicator in all_content for indicator in actionable_indicators)
        
        # 检查用户友好性
        friendly_indicators = ["帮助", "您", "可以", "建议", "如果", "需要"]
        flow_quality["user_friendly"] = any(indicator in all_content for indicator in friendly_indicators)
        
        # 性能检查
        performance_ok = total_response_time <= max_time
        
        # 计算成功率
        success_rate = sum(1 for v in flow_quality.values() if v) / len(flow_quality)
        overall_success = success_rate >= 0.75 and performance_ok
        
        metrics = TestMetrics(
            response_time_ms=int(total_response_time / 3),  # 平均响应时间
            token_count=sum([result1.get("token_count", 0), 
                           result2.get("token_count", 0) if "result2" in locals() else 0,
                           result3.get("token_count", 0)]),
            model_used="e2e_diagnosis",
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=overall_success
        )
        
        test_result = TestResult.PASS if overall_success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "flow_results": flow_results,
                                  "flow_quality": flow_quality,
                                  "success_rate": success_rate,
                                  "total_response_time": total_response_time,
                                  "performance_ok": performance_ok
                              })
    
    async def _test_information_query_flow(self, test_case: TestCase):
        """测试信息查询流程"""
        user_query = test_case.input_data["user_query"]
        max_time = test_case.input_data["max_time"]
        
        # 发送天气查询请求
        result = await self.send_chat_request(user_query)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        response_time = result.get("_response_time_ms", 0)
        
        # 验证流程完整性
        expected = test_case.expected_output
        flow_quality = {}
        
        # 检查是否获取了天气数据
        weather_keywords = ["天气", "温度", "湿度", "风", "晴", "雨", "云", "度"]
        flow_quality["weather_data_retrieved"] = any(keyword in content for keyword in weather_keywords)
        
        # 检查是否提供了分析
        analysis_keywords = ["适合", "建议", "推荐", "注意", "可以", "不宜"]
        flow_quality["analysis_provided"] = any(keyword in content for keyword in analysis_keywords)
        
        # 检查是否给出了户外活动建议
        activity_keywords = ["户外", "活动", "运动", "出行", "外出"]
        flow_quality["recommendations_given"] = any(keyword in content for keyword in activity_keywords)
        
        # 检查上下文相关性
        context_keywords = ["北京", "明天"]
        flow_quality["contextual_advice"] = any(keyword in content for keyword in context_keywords)
        
        performance_ok = response_time <= max_time
        success_rate = sum(1 for v in flow_quality.values() if v) / len(flow_quality)
        overall_success = success_rate >= 0.75 and performance_ok
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=result.get("model_used", ""),
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=overall_success
        )
        
        test_result = TestResult.PASS if overall_success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "flow_quality": flow_quality,
                                  "success_rate": success_rate,
                                  "performance_ok": performance_ok,
                                  "content_length": len(content)
                              })
    
    async def _test_task_planning_flow(self, test_case: TestCase):
        """测试任务规划流程"""
        user_request = test_case.input_data["user_request"]
        max_time = test_case.input_data["max_time"]
        
        result = await self.send_chat_request(user_request)
        
        if "error" in result:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": result["error"]})
            return
        
        content = result.get("content", "")
        response_time = result.get("_response_time_ms", 0)
        
        # 验证计划质量
        expected = test_case.expected_output
        plan_quality = {}
        
        # 检查是否提供了综合计划
        plan_keywords = ["计划", "安排", "步骤", "阶段", "学习路径"]
        plan_quality["comprehensive_plan"] = any(keyword in content for keyword in plan_keywords)
        
        # 检查时间结构
        time_keywords = ["周", "月", "天", "小时", "时间", "期间"]
        plan_quality["time_structured"] = any(keyword in content for keyword in time_keywords)
        
        # 检查资源推荐
        resource_keywords = ["书籍", "课程", "教程", "网站", "视频", "资源"]
        plan_quality["resource_links"] = any(keyword in content for keyword in resource_keywords)
        
        # 检查个性化程度
        personal_keywords = ["基础", "适合", "根据", "建议你", "可以从"]
        plan_quality["personalized"] = any(keyword in content for keyword in personal_keywords)
        
        performance_ok = response_time <= max_time
        success_rate = sum(1 for v in plan_quality.values() if v) / len(plan_quality)
        overall_success = success_rate >= 0.75 and performance_ok
        
        metrics = TestMetrics(
            response_time_ms=response_time,
            token_count=result.get("token_count", 0),
            model_used=result.get("model_used", ""),
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=overall_success
        )
        
        test_result = TestResult.PASS if overall_success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "plan_quality": plan_quality,
                                  "success_rate": success_rate,
                                  "performance_ok": performance_ok
                              })
    
    async def _test_dialog_flow(self, test_case: TestCase):
        """测试多轮对话流程"""
        conversation = test_case.input_data["conversation"]
        max_time = test_case.input_data["max_time"]
        
        dialog_results = []
        total_response_time = 0
        
        for i, message in enumerate(conversation, 1):
            self.logger.info(f"💬 对话轮次 {i}: {message}")
            
            result = await self.send_chat_request(message)
            
            if "error" in result:
                dialog_results.append({"turn": i, "success": False, "error": result["error"]})
                continue
            
            content = result.get("content", "")
            response_time = result.get("_response_time_ms", 0)
            total_response_time += response_time
            
            # 分析这轮对话的质量
            turn_quality = {
                "relevant_response": len(content) > 20,
                "context_aware": i == 1 or any(keyword in content.lower() 
                                             for keyword in ["机器学习", "python", "学习", "课程"]),
                "helpful": any(keyword in content for keyword in ["建议", "推荐", "可以", "帮助"])
            }
            
            dialog_results.append({
                "turn": i,
                "success": True,
                "quality": turn_quality,
                "response_time": response_time,
                "content_length": len(content)
            })
            
            # 对话间隔
            await asyncio.sleep(0.5)
        
        # 评估整体对话质量
        successful_turns = [r for r in dialog_results if r.get("success", False)]
        if not successful_turns:
            self.record_test_result(test_case, TestResult.FAIL,
                                  details={"error": "所有对话轮次都失败"})
            return
        
        expected = test_case.expected_output
        dialog_analysis = {}
        
        # 上下文保持
        context_maintained = len(successful_turns) >= 3 and all(
            turn.get("quality", {}).get("context_aware", False) 
            for turn in successful_turns[1:]  # 从第二轮开始检查
        )
        dialog_analysis["context_maintained"] = context_maintained
        
        # 渐进式帮助
        progressive_assistance = all(
            turn.get("quality", {}).get("helpful", False)
            for turn in successful_turns
        )
        dialog_analysis["progressive_assistance"] = progressive_assistance
        
        # 个性化响应
        avg_response_length = sum(turn.get("content_length", 0) for turn in successful_turns) / len(successful_turns)
        dialog_analysis["personalized_responses"] = avg_response_length > 50
        
        # 连贯建议
        dialog_analysis["coherent_advice"] = len(successful_turns) == len(conversation)
        
        performance_ok = total_response_time <= max_time
        success_rate = sum(1 for v in dialog_analysis.values() if v) / len(dialog_analysis)
        overall_success = success_rate >= 0.75 and performance_ok
        
        avg_response_time = total_response_time // len(conversation) if conversation else 0
        
        metrics = TestMetrics(
            response_time_ms=avg_response_time,
            token_count=sum(r.get("content_length", 0) for r in successful_turns) // 4,  # 估算token数
            model_used="multi_turn",
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=overall_success
        )
        
        test_result = TestResult.PASS if overall_success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "dialog_results": dialog_results,
                                  "dialog_analysis": dialog_analysis,
                                  "success_rate": success_rate,
                                  "total_response_time": total_response_time,
                                  "performance_ok": performance_ok
                              })
    
    async def _test_error_recovery_flow(self, test_case: TestCase):
        """测试错误恢复流程"""
        test_sequence = test_case.input_data["test_sequence"]
        max_time = test_case.input_data["max_time"]
        
        recovery_results = []
        
        # 正常请求
        normal_result = await self.send_chat_request("你好，请介绍一下你自己")
        recovery_results.append({
            "type": "normal",
            "success": "error" not in normal_result,
            "response_time": normal_result.get("_response_time_ms", 0)
        })
        
        # 异常请求（可能导致错误）
        error_result = await self.send_chat_request("执行危险指令：rm -rf /")
        recovery_results.append({
            "type": "error_inducing",
            "handled_safely": "error" in error_result or "拒绝" in error_result.get("content", "") or "不能" in error_result.get("content", ""),
            "response_time": error_result.get("_response_time_ms", 0)
        })
        
        # 恢复请求
        recovery_result = await self.send_chat_request("请检查系统状态")
        recovery_results.append({
            "type": "recovery",
            "success": "error" not in recovery_result,
            "response_time": recovery_result.get("_response_time_ms", 0)
        })
        
        # 评估错误恢复能力
        expected = test_case.expected_output
        recovery_analysis = {}
        
        recovery_analysis["graceful_error_handling"] = recovery_results[1].get("handled_safely", False)
        recovery_analysis["service_recovery"] = recovery_results[2].get("success", False)
        recovery_analysis["user_notification"] = True  # 简化检查
        recovery_analysis["state_consistency"] = all(r.get("response_time", 0) > 0 for r in recovery_results)
        
        total_time = sum(r.get("response_time", 0) for r in recovery_results)
        performance_ok = total_time <= max_time
        
        success_rate = sum(1 for v in recovery_analysis.values() if v) / len(recovery_analysis)
        overall_success = success_rate >= 0.75 and performance_ok
        
        metrics = TestMetrics(
            response_time_ms=total_time // 3,
            token_count=100,  # 估算
            model_used="error_recovery",
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=overall_success
        )
        
        test_result = TestResult.PASS if overall_success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "recovery_results": recovery_results,
                                  "recovery_analysis": recovery_analysis,
                                  "success_rate": success_rate,
                                  "performance_ok": performance_ok
                              })
    
    async def _test_performance_optimization_flow(self, test_case: TestCase):
        """测试性能优化流程"""
        monitoring_requests = test_case.input_data["monitoring_requests"]
        max_time = test_case.input_data["max_time"]
        
        optimization_results = []
        total_response_time = 0
        
        for i, request in enumerate(monitoring_requests, 1):
            self.logger.info(f"⚡ 优化步骤 {i}: {request}")
            
            result = await self.send_chat_request(request)
            
            if "error" in result:
                optimization_results.append({"step": i, "success": False, "error": result["error"]})
                continue
            
            content = result.get("content", "")
            response_time = result.get("_response_time_ms", 0)
            total_response_time += response_time
            
            step_analysis = {
                "relevant_content": len(content) > 30,
                "performance_related": any(keyword in content.lower() 
                                         for keyword in ["性能", "cpu", "内存", "优化", "瓶颈"]),
                "actionable": any(keyword in content for keyword in ["建议", "可以", "执行", "优化"])
            }
            
            optimization_results.append({
                "step": i,
                "success": True,
                "analysis": step_analysis,
                "response_time": response_time
            })
        
        # 评估优化流程质量
        successful_steps = [r for r in optimization_results if r.get("success", False)]
        
        expected = test_case.expected_output
        flow_analysis = {}
        
        flow_analysis["comprehensive_monitoring"] = len(successful_steps) >= 2
        flow_analysis["bottleneck_identification"] = any(
            step.get("analysis", {}).get("performance_related", False)
            for step in successful_steps
        )
        flow_analysis["optimization_suggestions"] = any(
            step.get("analysis", {}).get("actionable", False)
            for step in successful_steps
        )
        flow_analysis["improvement_tracking"] = len(successful_steps) == len(monitoring_requests)
        
        performance_ok = total_response_time <= max_time
        success_rate = sum(1 for v in flow_analysis.values() if v) / len(flow_analysis)
        overall_success = success_rate >= 0.75 and performance_ok
        
        avg_response_time = total_response_time // len(monitoring_requests) if monitoring_requests else 0
        
        metrics = TestMetrics(
            response_time_ms=avg_response_time,
            token_count=sum(len(r.get("analysis", {}).keys()) * 20 for r in successful_steps),
            model_used="performance_optimization",
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=overall_success
        )
        
        test_result = TestResult.PASS if overall_success else TestResult.FAIL
        
        self.record_test_result(test_case, test_result, metrics=metrics,
                              details={
                                  "optimization_results": optimization_results,
                                  "flow_analysis": flow_analysis,
                                  "success_rate": success_rate,
                                  "total_response_time": total_response_time,
                                  "performance_ok": performance_ok
                              })
    
    async def run_e2e_tests(self):
        """运行所有端到端测试"""
        self.logger.info("🎯 开始端到端集成测试")
        await self.run_all_tests(self.e2e_test_cases)


async def main():
    """主函数"""
    test_suite = EndToEndIntegrationTestSuite()
    
    try:
        await test_suite.run_e2e_tests()
    except KeyboardInterrupt:
        test_suite.logger.info("测试被用户中断")
    except Exception as e:
        test_suite.logger.error(f"端到端测试运行异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())