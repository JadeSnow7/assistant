#!/usr/bin/env python3
"""
CLI测试套件运行器
统一运行所有CLI相关测试并生成报告
"""
import asyncio
import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.cli.test_cli_commands import CLICommandRoutingTestSuite, CLIDisplayTestSuite
from tests.cli.test_cli_performance import CLIPerformanceTestSuite, CLICompatibilityTestSuite


class CLITestRunner:
    """CLI测试运行器"""
    
    def __init__(self, base_url: str = "http://localhost:8000", output_dir: str = "test_reports"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 注册测试套件
        self.test_suites = {
            "commands": CLICommandRoutingTestSuite(base_url),
            "display": CLIDisplayTestSuite(base_url),
            "performance": CLIPerformanceTestSuite(base_url),
            "compatibility": CLICompatibilityTestSuite(base_url)
        }
        
        self.overall_results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_health_check(self) -> bool:
        """运行健康检查"""
        print("🏥 执行CLI测试环境健康检查...")
        
        try:
            # 检查Python环境
            python_version = sys.version_info
            if python_version < (3, 9):
                print(f"❌ Python版本过低: {python_version.major}.{python_version.minor} (需要 >= 3.9)")
                return False
            
            # 检查关键模块
            required_modules = ["rich", "textual", "asyncio", "pathlib"]
            for module_name in required_modules:
                try:
                    __import__(module_name)
                except ImportError as e:
                    print(f"❌ 缺少必需模块: {module_name} - {e}")
                    return False
            
            # 检查CLI脚本文件
            cli_scripts = [
                project_root / "start_cli.py",
                project_root / "ui" / "cli" / "modern_cli.py"
            ]
            
            for script in cli_scripts:
                if not script.exists():
                    print(f"❌ CLI脚本不存在: {script}")
                    return False
            
            print("✅ CLI测试环境健康检查通过")
            return True
            
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False
    
    async def run_single_suite(self, suite_name: str, suite) -> Dict[str, Any]:
        """运行单个测试套件"""
        print(f"\n🧪 开始运行CLI测试套件: {suite_name}")
        print("=" * 60)
        
        suite_start_time = time.time()
        
        try:
            # 根据套件类型运行相应的测试方法
            if suite_name == "commands":
                await suite.run_command_routing_tests()
            elif suite_name == "display":
                await suite.run_display_tests()
            elif suite_name == "performance":
                await suite.run_performance_tests()
            elif suite_name == "compatibility":
                await suite.run_compatibility_tests()
            
            suite_end_time = time.time()
            suite_duration = suite_end_time - suite_start_time
            
            # 获取测试报告
            report = suite.generate_test_report()
            report["suite_name"] = suite_name
            report["duration_seconds"] = round(suite_duration, 2)
            report["timestamp"] = time.time()
            
            print(f"✅ CLI测试套件 {suite_name} 完成")
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
            
            print(f"❌ CLI测试套件 {suite_name} 执行失败: {e}")
            return error_report
    
    async def run_all_suites(self, selected_suites: List[str] = None) -> Dict[str, Any]:
        """运行所有测试套件"""
        print("🚀 开始AI Assistant CLI完整测试")
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
        
        cli_specific_metrics = {
            "startup_times": [],
            "response_times": [],
            "memory_usage": [],
            "compatibility_scores": []
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
                
                # 收集性能指标
                performance_metrics["suite_durations"].append(report.get("duration_seconds", 0))
                
                # CLI特定指标
                if "performance" in report and "test_details" in report:
                    for test in report["test_details"]:
                        test_name = test.get("test_name", "")
                        details = test.get("details", {})
                        
                        if "startup" in test_name:
                            if "average_startup_time" in details:
                                cli_specific_metrics["startup_times"].append(details["average_startup_time"])
                        elif "response" in test_name:
                            if "average_response_time" in details:
                                cli_specific_metrics["response_times"].append(details["average_response_time"])
                        elif "memory" in test_name:
                            if "memory_mb" in details:
                                cli_specific_metrics["memory_usage"].append(details["memory_mb"])
        
        # 计算平均值
        if performance_metrics["suite_durations"]:
            performance_metrics["average_suite_duration"] = sum(performance_metrics["suite_durations"]) / len(performance_metrics["suite_durations"])
        
        if cli_specific_metrics["startup_times"]:
            cli_specific_metrics["average_startup_time"] = sum(cli_specific_metrics["startup_times"]) / len(cli_specific_metrics["startup_times"])
        
        if cli_specific_metrics["response_times"]:
            cli_specific_metrics["average_response_time"] = sum(cli_specific_metrics["response_times"]) / len(cli_specific_metrics["response_times"])
        
        if cli_specific_metrics["memory_usage"]:
            cli_specific_metrics["average_memory_usage"] = sum(cli_specific_metrics["memory_usage"]) / len(cli_specific_metrics["memory_usage"])
        
        # 计算成功率
        if overall_stats["total_tests"] > 0:
            success_rate = (overall_stats["passed"] / overall_stats["total_tests"]) * 100
            overall_stats["success_rate"] = f"{success_rate:.1f}%"
        else:
            overall_stats["success_rate"] = "0%"
        
        return {
            "test_type": "CLI Complete Test Suite",
            "timestamp": self.end_time,
            "total_duration": total_duration,
            "summary": overall_stats,
            "suite_summaries": suite_summaries,
            "performance_metrics": performance_metrics,
            "cli_specific_metrics": cli_specific_metrics,
            "detailed_results": self.overall_results,
            "environment": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform,
                "base_url": self.base_url
            }
        }
    
    def save_reports(self, overall_report: Dict[str, Any]):
        """保存测试报告"""
        timestamp = int(time.time())
        
        # 保存综合报告
        overall_report_file = self.output_dir / f"cli_test_report_{timestamp}.json"
        with open(overall_report_file, "w", encoding="utf-8") as f:
            json.dump(overall_report, f, ensure_ascii=False, indent=2)
        
        # 保存各套件详细报告
        for suite_name, report in self.overall_results.items():
            suite_report_file = self.output_dir / f"cli_{suite_name}_report_{timestamp}.json"
            with open(suite_report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成HTML报告
        self._generate_html_report(overall_report, timestamp)
        
        print(f"\n📊 测试报告已保存到: {self.output_dir}")
        print(f"   - 综合报告: cli_test_report_{timestamp}.json")
        print(f"   - HTML报告: cli_test_report_{timestamp}.html")
    
    def _generate_html_report(self, overall_report: Dict[str, Any], timestamp: int):
        """生成HTML格式的测试报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Assistant CLI测试报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric h3 {{ margin: 0 0 10px 0; color: #495057; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
        .suite-details {{ margin: 20px 0; }}
        .suite-name {{ background: #e9ecef; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 AI Assistant CLI测试报告</h1>
        <p><strong>生成时间:</strong> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}</p>
        <p><strong>执行时长:</strong> {overall_report['total_duration']:.2f}秒</p>
        
        <div class="summary">
            <div class="metric">
                <h3>总测试数</h3>
                <div class="value">{overall_report['summary']['total_tests']}</div>
            </div>
            <div class="metric">
                <h3>通过</h3>
                <div class="value success">{overall_report['summary']['passed']}</div>
            </div>
            <div class="metric">
                <h3>失败</h3>
                <div class="value danger">{overall_report['summary']['failed']}</div>
            </div>
            <div class="metric">
                <h3>成功率</h3>
                <div class="value">{overall_report['summary']['success_rate']}</div>
            </div>
        </div>
        
        <h2>📋 测试套件摘要</h2>
        <table>
            <thead>
                <tr>
                    <th>测试套件</th>
                    <th>测试数量</th>
                    <th>成功率</th>
                    <th>执行时间(秒)</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for suite_name, summary in overall_report["suite_summaries"].items():
            html_content += f"""
                <tr>
                    <td>{suite_name}</td>
                    <td>{summary['tests']}</td>
                    <td>{summary['success_rate']}</td>
                    <td>{summary['duration']:.2f}</td>
                </tr>
            """
        
        html_content += """
            </tbody>
        </table>
        
        <h2>⚡ CLI性能指标</h2>
        <div class="summary">
        """
        
        cli_metrics = overall_report.get("cli_specific_metrics", {})
        if cli_metrics.get("average_startup_time"):
            html_content += f"""
            <div class="metric">
                <h3>平均启动时间</h3>
                <div class="value">{cli_metrics['average_startup_time']:.2f}s</div>
            </div>
            """
        
        if cli_metrics.get("average_response_time"):
            html_content += f"""
            <div class="metric">
                <h3>平均响应时间</h3>
                <div class="value">{cli_metrics['average_response_time']:.2f}s</div>
            </div>
            """
        
        if cli_metrics.get("average_memory_usage"):
            html_content += f"""
            <div class="metric">
                <h3>平均内存使用</h3>
                <div class="value">{cli_metrics['average_memory_usage']:.1f}MB</div>
            </div>
            """
        
        html_content += """
        </div>
        
        <h2>🔍 详细结果</h2>
        """
        
        for suite_name, report in overall_report["detailed_results"].items():
            html_content += f"""
            <div class="suite-details">
                <div class="suite-name">
                    <h3>{suite_name.upper()} 测试套件</h3>
                </div>
            """
            
            if "test_details" in report:
                html_content += """
                <table>
                    <thead>
                        <tr>
                            <th>测试名称</th>
                            <th>状态</th>
                            <th>响应时间</th>
                            <th>消息</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for test in report["test_details"]:
                    status_class = "success" if test.get("success") else "danger"
                    status_text = "通过" if test.get("success") else "失败"
                    
                    html_content += f"""
                        <tr>
                            <td>{test.get('test_name', 'Unknown')}</td>
                            <td class="{status_class}">{status_text}</td>
                            <td>{test.get('response_time', 0):.3f}s</td>
                            <td>{test.get('message', '')}</td>
                        </tr>
                    """
                
                html_content += """
                    </tbody>
                </table>
                """
            
            html_content += "</div>"
        
        html_content += """
        </div>
    </div>
</body>
</html>
        """
        
        html_report_file = self.output_dir / f"cli_test_report_{timestamp}.html"
        with open(html_report_file, "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def print_summary(self, overall_report: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "="*80)
        print("🧪 AI Assistant CLI测试完整报告")
        print("="*80)
        
        summary = overall_report["summary"]
        print(f"📊 总测试数: {summary['total_tests']}")
        print(f"✅ 通过: {summary['passed']}")
        print(f"❌ 失败: {summary['failed']}")
        print(f"⚠️ 错误: {summary['errors']}")
        print(f"📈 成功率: {summary['success_rate']}")
        print(f"⏱️ 总执行时间: {overall_report['total_duration']:.2f}秒")
        
        print("\n📋 各套件结果:")
        for suite_name, summary in overall_report["suite_summaries"].items():
            print(f"  {suite_name}: {summary['tests']}测试, {summary['success_rate']}通过率, {summary['duration']:.2f}s")
        
        # CLI特定指标
        cli_metrics = overall_report.get("cli_specific_metrics", {})
        if cli_metrics:
            print("\n⚡ CLI性能指标:")
            if cli_metrics.get("average_startup_time"):
                print(f"  平均启动时间: {cli_metrics['average_startup_time']:.2f}s")
            if cli_metrics.get("average_response_time"):
                print(f"  平均响应时间: {cli_metrics['average_response_time']:.2f}s")
            if cli_metrics.get("average_memory_usage"):
                print(f"  平均内存使用: {cli_metrics['average_memory_usage']:.1f}MB")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI Assistant CLI测试套件")
    parser.add_argument("--url", default="http://localhost:8000", help="API服务地址")
    parser.add_argument("--output", default="test_reports", help="测试报告输出目录")
    parser.add_argument("--suites", nargs="+", 
                       choices=["commands", "display", "performance", "compatibility"],
                       help="指定要运行的测试套件")
    parser.add_argument("--no-health-check", action="store_true", help="跳过健康检查")
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = CLITestRunner(args.url, args.output)
    
    # 健康检查
    if not args.no_health_check:
        if not await runner.run_health_check():
            print("❌ 健康检查失败，退出测试")
            sys.exit(1)
    
    # 运行测试
    try:
        overall_report = await runner.run_all_suites(args.suites)
        
        # 显示摘要
        runner.print_summary(overall_report)
        
        # 保存报告
        runner.save_reports(overall_report)
        
        # 根据结果设置退出码
        if overall_report["summary"]["failed"] > 0 or overall_report["summary"]["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())