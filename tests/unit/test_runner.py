#!/usr/bin/env python3
"""
自动化测试套件运行器
提供统一的测试执行、报告生成和结果管理功能
"""
import asyncio
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.unit.base import BaseTestSuite, TestResult
from tests.unit.test_dialog_system import DialogSystemTestSuite
from tests.unit.test_intelligent_routing import IntelligentRoutingTestSuite
from tests.unit.test_system_commands import SystemCommandTestSuite
from tests.unit.test_resource_management import ResourceManagementTestSuite
from tests.e2e.test_integration_flows import EndToEndIntegrationTestSuite


class AutomatedTestRunner:
    """自动化测试运行器"""
    
    def __init__(self, base_url: str = "http://localhost:8000", output_dir: str = "test_reports"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 注册所有测试套件
        self.test_suites = {
            "dialog": DialogSystemTestSuite(base_url),
            "routing": IntelligentRoutingTestSuite(base_url),
            "commands": SystemCommandTestSuite(base_url),
            "resources": ResourceManagementTestSuite(base_url),
            "e2e": EndToEndIntegrationTestSuite(base_url)
        }
        
        self.overall_results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_health_check(self) -> bool:
        """运行健康检查"""
        print("🏥 执行系统健康检查...")
        
        try:
            # 使用基础测试套件进行健康检查
            base_suite = BaseTestSuite(self.base_url)
            health_result = await base_suite.get_health_status()
            
            if "error" in health_result:
                print(f"❌ 健康检查失败: {health_result['error']}")
                return False
            
            print("✅ 系统健康检查通过")
            return True
            
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False
    
    async def run_single_suite(self, suite_name: str, suite: BaseTestSuite) -> Dict[str, Any]:
        """运行单个测试套件"""
        print(f"\n🧪 开始运行测试套件: {suite_name}")
        print("=" * 60)
        
        suite_start_time = time.time()
        
        try:
            # 根据套件类型运行相应的测试方法
            if hasattr(suite, 'run_dialog_tests'):
                await suite.run_dialog_tests()
            elif hasattr(suite, 'run_routing_tests'):
                await suite.run_routing_tests()
            elif hasattr(suite, 'run_command_tests'):
                await suite.run_command_tests()
            elif hasattr(suite, 'run_resource_tests'):
                await suite.run_resource_tests()
            elif hasattr(suite, 'run_e2e_tests'):
                await suite.run_e2e_tests()
            else:
                # 默认运行所有测试用例
                if hasattr(suite, 'dialog_test_cases'):
                    await suite.run_all_tests(suite.dialog_test_cases)
                elif hasattr(suite, 'routing_test_cases'):
                    await suite.run_all_tests(suite.routing_test_cases)
                elif hasattr(suite, 'command_test_cases'):
                    await suite.run_all_tests(suite.command_test_cases)
                elif hasattr(suite, 'resource_test_cases'):
                    await suite.run_all_tests(suite.resource_test_cases)
                elif hasattr(suite, 'e2e_test_cases'):
                    await suite.run_all_tests(suite.e2e_test_cases)
            
            suite_end_time = time.time()
            suite_duration = suite_end_time - suite_start_time
            
            # 获取测试报告
            report = suite.generate_test_report()
            report["suite_name"] = suite_name
            report["duration_seconds"] = round(suite_duration, 2)
            report["timestamp"] = time.time()
            
            print(f"✅ 测试套件 {suite_name} 完成")
            print(f"⏱️ 执行时间: {suite_duration:.2f}秒")
            
            return report
            
        except Exception as e:
            suite_end_time = time.time()
            suite_duration = suite_end_time - suite_start_time
            
            error_report = {
                "suite_name": suite_name,
                "error": str(e),
                "duration_seconds": round(suite_duration, 2),
                "timestamp": time.time(),
                "summary": {
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 1,
                    "skipped": 0,
                    "success_rate": "0%"
                }
            }
            
            print(f"❌ 测试套件 {suite_name} 执行失败: {e}")
            return error_report
    
    async def run_all_suites(self, selected_suites: Optional[List[str]] = None) -> Dict[str, Any]:
        """运行所有测试套件"""
        print("🚀 开始AI助手功能测试与对话验证")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # 确定要运行的测试套件
        if selected_suites:
            suites_to_run = {name: suite for name, suite in self.test_suites.items() 
                           if name in selected_suites}
        else:
            suites_to_run = self.test_suites
        
        # 运行每个测试套件
        for suite_name, suite in suites_to_run.items():
            suite_report = await self.run_single_suite(suite_name, suite)
            self.overall_results[suite_name] = suite_report
        
        self.end_time = time.time()
        
        # 生成综合报告
        overall_report = self._generate_overall_report()
        
        return overall_report
    
    def _generate_overall_report(self) -> Dict[str, Any]:
        """生成综合测试报告"""
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        # 汇总统计
        overall_stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0
        }
        
        suite_summaries = {}
        performance_metrics = {
            "total_response_times": [],
            "suite_durations": [],
            "average_response_time": 0,
            "total_execution_time": total_duration
        }
        
        # 汇总各套件结果
        for suite_name, report in self.overall_results.items():
            if "summary" in report:
                summary = report["summary"]
                overall_stats["total_tests"] += summary.get("total_tests", 0)
                overall_stats["passed"] += summary.get("passed", 0)
                overall_stats["failed"] += summary.get("failed", 0)
                overall_stats["errors"] += summary.get("errors", 0)
                overall_stats["skipped"] += summary.get("skipped", 0)
                
                suite_summaries[suite_name] = {
                    "tests": summary.get("total_tests", 0),
                    "success_rate": summary.get("success_rate", "0%"),
                    "duration": report.get("duration_seconds", 0)
                }
                
                # 性能指标
                if "performance" in report:
                    perf = report["performance"]
                    if perf.get("avg_response_time_ms", 0) > 0:
                        performance_metrics["total_response_times"].append(perf["avg_response_time_ms"])
                
                performance_metrics["suite_durations"].append(report.get("duration_seconds", 0))
        
        # 计算综合成功率
        if overall_stats["total_tests"] > 0:
            success_rate = (overall_stats["passed"] / overall_stats["total_tests"]) * 100
            overall_stats["success_rate"] = f"{success_rate:.1f}%"
        else:
            overall_stats["success_rate"] = "0%"
        
        # 计算平均响应时间
        if performance_metrics["total_response_times"]:
            avg_response_time = sum(performance_metrics["total_response_times"]) / len(performance_metrics["total_response_times"])
            performance_metrics["average_response_time"] = round(avg_response_time, 2)
        
        # 测试质量评估
        quality_assessment = self._assess_test_quality(overall_stats, performance_metrics)
        
        overall_report = {
            "test_execution_summary": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)),
                "total_duration_seconds": round(total_duration, 2),
                "suites_executed": len(self.overall_results),
                "base_url": self.base_url
            },
            "overall_statistics": overall_stats,
            "suite_summaries": suite_summaries,
            "performance_metrics": performance_metrics,
            "quality_assessment": quality_assessment,
            "detailed_results": self.overall_results
        }
        
        return overall_report
    
    def _assess_test_quality(self, stats: Dict[str, Any], performance: Dict[str, Any]) -> Dict[str, Any]:
        """评估测试质量"""
        assessment = {
            "overall_health": "UNKNOWN",
            "reliability_score": 0.0,
            "performance_score": 0.0,
            "coverage_score": 0.0,
            "recommendations": []
        }
        
        # 可靠性评分（基于成功率）
        success_rate_str = stats.get("success_rate", "0%")
        success_rate = float(success_rate_str.replace("%", ""))
        
        if success_rate >= 95:
            assessment["reliability_score"] = 1.0
            assessment["overall_health"] = "EXCELLENT"
        elif success_rate >= 85:
            assessment["reliability_score"] = 0.8
            assessment["overall_health"] = "GOOD"
        elif success_rate >= 70:
            assessment["reliability_score"] = 0.6
            assessment["overall_health"] = "FAIR"
        else:
            assessment["reliability_score"] = 0.3
            assessment["overall_health"] = "POOR"
        
        # 性能评分（基于响应时间）
        avg_response_time = performance.get("average_response_time", 0)
        if avg_response_time <= 1000:  # 1秒以内
            assessment["performance_score"] = 1.0
        elif avg_response_time <= 3000:  # 3秒以内
            assessment["performance_score"] = 0.8
        elif avg_response_time <= 5000:  # 5秒以内
            assessment["performance_score"] = 0.6
        else:
            assessment["performance_score"] = 0.3
        
        # 覆盖率评分（基于测试套件数量和测试用例数量）
        total_tests = stats.get("total_tests", 0)
        suites_count = len(self.overall_results)
        
        if total_tests >= 20 and suites_count >= 4:
            assessment["coverage_score"] = 1.0
        elif total_tests >= 15 and suites_count >= 3:
            assessment["coverage_score"] = 0.8
        elif total_tests >= 10 and suites_count >= 2:
            assessment["coverage_score"] = 0.6
        else:
            assessment["coverage_score"] = 0.4
        
        # 生成建议
        if assessment["reliability_score"] < 0.8:
            assessment["recommendations"].append("建议修复失败的测试用例，提高系统稳定性")
        
        if assessment["performance_score"] < 0.8:
            assessment["recommendations"].append("建议优化响应时间，目标响应时间应在3秒以内")
        
        if assessment["coverage_score"] < 0.8:
            assessment["recommendations"].append("建议增加更多测试用例，提高测试覆盖率")
        
        if stats.get("errors", 0) > 0:
            assessment["recommendations"].append("建议检查并修复测试执行过程中的错误")
        
        return assessment
    
    def save_report(self, report: Dict[str, Any], format_type: str = "json") -> str:
        """保存测试报告"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        if format_type == "json":
            filename = f"test_report_{timestamp}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
        elif format_type == "html":
            filename = f"test_report_{timestamp}.html"
            filepath = self.output_dir / filename
            
            html_content = self._generate_html_report(report)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        else:
            raise ValueError(f"不支持的报告格式: {format_type}")
        
        return str(filepath)
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """生成HTML格式的测试报告"""
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI助手功能测试报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .metric-label { color: #666; margin-top: 5px; }
        .suite-results { margin-bottom: 30px; }
        .suite { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 6px; }
        .suite-header { font-weight: bold; margin-bottom: 10px; }
        .success { color: #28a745; }
        .failure { color: #dc3545; }
        .warning { color: #ffc107; }
        .recommendations { background: #e7f3ff; padding: 15px; border-radius: 6px; margin-top: 20px; }
        .quality-indicator { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; }
        .excellent { background-color: #28a745; }
        .good { background-color: #17a2b8; }
        .fair { background-color: #ffc107; }
        .poor { background-color: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI助手功能测试报告</h1>
            <p>测试时间: {timestamp}</p>
            <p>总执行时间: {duration:.2f}秒</p>
        </div>
        
        <div class="summary">
            <div class="metric-card">
                <div class="metric-value">{total_tests}</div>
                <div class="metric-label">总测试数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{passed}</div>
                <div class="metric-label">通过</div>
            </div>
            <div class="metric-card">
                <div class="metric-value failure">{failed}</div>
                <div class="metric-label">失败</div>
            </div>
            <div class="metric-card">
                <div class="metric-value warning">{errors}</div>
                <div class="metric-label">错误</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{success_rate}</div>
                <div class="metric-label">成功率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{avg_response_time:.0f}ms</div>
                <div class="metric-label">平均响应时间</div>
            </div>
        </div>
        
        <div class="quality-section">
            <h2>质量评估</h2>
            <p>系统健康状况: <span class="quality-indicator {health_class}">{health_status}</span></p>
            <p>可靠性评分: {reliability_score:.1%}</p>
            <p>性能评分: {performance_score:.1%}</p>
            <p>覆盖率评分: {coverage_score:.1%}</p>
        </div>
        
        <div class="suite-results">
            <h2>测试套件结果</h2>
            {suite_details}
        </div>
        
        {recommendations_section}
    </div>
</body>
</html>
        """
        
        # 准备数据
        execution_summary = report.get("test_execution_summary", {})
        stats = report.get("overall_statistics", {})
        performance = report.get("performance_metrics", {})
        quality = report.get("quality_assessment", {})
        suite_summaries = report.get("suite_summaries", {})
        
        # 生成套件详情
        suite_details = ""
        for suite_name, summary in suite_summaries.items():
            suite_details += f"""
            <div class="suite">
                <div class="suite-header">{suite_name.upper()} 测试套件</div>
                <p>测试数量: {summary.get('tests', 0)}</p>
                <p>成功率: {summary.get('success_rate', '0%')}</p>
                <p>执行时间: {summary.get('duration', 0):.2f}秒</p>
            </div>
            """
        
        # 生成建议部分
        recommendations = quality.get("recommendations", [])
        if recommendations:
            recommendations_section = f"""
            <div class="recommendations">
                <h3>改进建议</h3>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in recommendations)}
                </ul>
            </div>
            """
        else:
            recommendations_section = ""
        
        # 确定健康状况样式
        health_status = quality.get("overall_health", "UNKNOWN")
        health_class = health_status.lower()
        
        return html_template.format(
            timestamp=execution_summary.get("timestamp", "未知"),
            duration=execution_summary.get("total_duration_seconds", 0),
            total_tests=stats.get("total_tests", 0),
            passed=stats.get("passed", 0),
            failed=stats.get("failed", 0),
            errors=stats.get("errors", 0),
            success_rate=stats.get("success_rate", "0%"),
            avg_response_time=performance.get("average_response_time", 0),
            health_status=health_status,
            health_class=health_class,
            reliability_score=quality.get("reliability_score", 0),
            performance_score=quality.get("performance_score", 0),
            coverage_score=quality.get("coverage_score", 0),
            suite_details=suite_details,
            recommendations_section=recommendations_section
        )
    
    def print_summary(self, report: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "=" * 80)
        print("📊 AI助手功能测试完成摘要")
        print("=" * 80)
        
        execution_summary = report.get("test_execution_summary", {})
        stats = report.get("overall_statistics", {})
        performance = report.get("performance_metrics", {})
        quality = report.get("quality_assessment", {})
        
        print(f"🕐 测试时间: {execution_summary.get('timestamp', '未知')}")
        print(f"⏱️ 总执行时间: {execution_summary.get('total_duration_seconds', 0):.2f}秒")
        print(f"🧪 测试套件数: {execution_summary.get('suites_executed', 0)}")
        print(f"📈 总测试数: {stats.get('total_tests', 0)}")
        print(f"✅ 通过: {stats.get('passed', 0)}")
        print(f"❌ 失败: {stats.get('failed', 0)}")
        print(f"💥 错误: {stats.get('errors', 0)}")
        print(f"⏭️ 跳过: {stats.get('skipped', 0)}")
        print(f"📊 成功率: {stats.get('success_rate', '0%')}")
        print(f"⚡ 平均响应时间: {performance.get('average_response_time', 0):.0f}ms")
        
        # 质量评估
        print(f"\n🏥 系统健康状况: {quality.get('overall_health', 'UNKNOWN')}")
        print(f"🔒 可靠性评分: {quality.get('reliability_score', 0):.1%}")
        print(f"⚡ 性能评分: {quality.get('performance_score', 0):.1%}")
        print(f"📋 覆盖率评分: {quality.get('coverage_score', 0):.1%}")
        
        # 建议
        recommendations = quality.get("recommendations", [])
        if recommendations:
            print(f"\n💡 改进建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        print("=" * 80)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI助手自动化测试运行器")
    parser.add_argument("--url", default="http://localhost:8000", help="服务器URL")
    parser.add_argument("--suites", nargs="+", choices=["dialog", "routing", "commands", "resources", "e2e"],
                       help="指定要运行的测试套件")
    parser.add_argument("--output", default="test_reports", help="报告输出目录")
    parser.add_argument("--format", choices=["json", "html"], default="json", help="报告格式")
    parser.add_argument("--skip-health-check", action="store_true", help="跳过健康检查")
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = AutomatedTestRunner(base_url=args.url, output_dir=args.output)
    
    try:
        # 健康检查
        if not args.skip_health_check:
            health_ok = await runner.run_health_check()
            if not health_ok:
                print("❌ 系统健康检查失败，建议检查服务状态后重试")
                return 1
        
        # 运行测试
        report = await runner.run_all_suites(args.suites)
        
        # 保存报告
        report_path = runner.save_report(report, args.format)
        print(f"\n📄 测试报告已保存: {report_path}")
        
        # 打印摘要
        runner.print_summary(report)
        
        # 根据测试结果确定退出码
        stats = report.get("overall_statistics", {})
        if stats.get("failed", 0) > 0 or stats.get("errors", 0) > 0:
            return 1
        else:
            return 0
            
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试运行异常: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)