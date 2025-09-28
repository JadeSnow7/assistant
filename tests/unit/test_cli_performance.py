#!/usr/bin/env python3
"""
CLI性能和兼容性测试
测试CLI的启动性能、响应时间和跨平台兼容性
"""
import asyncio
import sys
import time
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import json

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.unit.cli_test_base import CLITestBase, CLIPerformanceTest, CLICompatibilityTest, TestResult


class CLIPerformanceTestSuite(CLIPerformanceTest):
    """CLI性能测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.performance_benchmarks = {
            "startup_time_threshold": 3.0,  # 秒
            "response_time_threshold": 2.0,  # 秒
            "memory_usage_threshold": 100,   # MB
            "cpu_usage_threshold": 50        # %
        }
    
    async def run_performance_tests(self):
        """运行性能测试"""
        print("⚡ 开始CLI性能测试")
        
        await self.setup_test_environment()
        
        try:
            # 启动时间测试
            startup_results = await self._test_startup_performance()
            self.test_results.extend(startup_results)
            
            # 响应时间测试
            response_results = await self._test_response_performance()
            self.test_results.extend(response_results)
            
            # 内存使用测试
            memory_results = await self._test_memory_usage()
            self.test_results.extend(memory_results)
            
            # 并发性能测试
            concurrent_results = await self._test_concurrent_performance()
            self.test_results.extend(concurrent_results)
            
        finally:
            await self.teardown_test_environment()
    
    async def _test_startup_performance(self) -> List[TestResult]:
        """测试启动性能"""
        results = []
        
        cli_scripts = [
            "start_cli.py",
            "ui/cli/modern_cli.py"
        ]
        
        for script in cli_scripts:
            test_name = f"startup_performance_{script.replace('/', '_').replace('.py', '')}"
            
            try:
                # 多次测量取平均值
                startup_times = []
                for i in range(5):
                    result = await self.measure_startup_time(script)
                    if result["success"]:
                        startup_times.append(result["startup_time"])
                
                if startup_times:
                    avg_startup_time = sum(startup_times) / len(startup_times)
                    min_startup_time = min(startup_times)
                    max_startup_time = max(startup_times)
                    
                    success = avg_startup_time <= self.performance_benchmarks["startup_time_threshold"]
                    
                    results.append(TestResult(
                        test_name=test_name,
                        success=success,
                        response_time=avg_startup_time,
                        message=f"平均启动时间: {avg_startup_time:.2f}s",
                        details={
                            "script": script,
                            "average_startup_time": avg_startup_time,
                            "min_startup_time": min_startup_time,
                            "max_startup_time": max_startup_time,
                            "threshold": self.performance_benchmarks["startup_time_threshold"],
                            "all_times": startup_times
                        }
                    ))
                else:
                    results.append(TestResult(
                        test_name=test_name,
                        success=False,
                        response_time=0,
                        message=f"无法测量 {script} 的启动时间",
                        details={"script": script, "error": "no_successful_measurements"}
                    ))
            
            except Exception as e:
                results.append(TestResult(
                    test_name=test_name,
                    success=False,
                    response_time=0,
                    message=f"启动性能测试失败: {str(e)}",
                    details={"script": script, "error": str(e)}
                ))
        
        return results
    
    async def _test_response_performance(self) -> List[TestResult]:
        """测试响应性能"""
        results = []
        
        test_inputs = [
            "你好",
            "help",
            "这是一个较长的测试消息，用来测试系统处理长文本的响应时间",
            "/status",
            "/health"
        ]
        
        scripts = ["start_cli.py", "ui/cli/modern_cli.py"]
        
        for script in scripts:
            test_name = f"response_performance_{script.replace('/', '_').replace('.py', '')}"
            
            try:
                result = await self.measure_response_time(script, test_inputs)
                avg_response_time = result["average_response_time"]
                
                success = avg_response_time <= self.performance_benchmarks["response_time_threshold"]
                
                results.append(TestResult(
                    test_name=test_name,
                    success=success,
                    response_time=avg_response_time,
                    message=f"平均响应时间: {avg_response_time:.2f}s",
                    details={
                        "script": script,
                        "average_response_time": avg_response_time,
                        "response_times": result["response_times"],
                        "threshold": self.performance_benchmarks["response_time_threshold"],
                        "total_tests": result["total_tests"]
                    }
                ))
            
            except Exception as e:
                results.append(TestResult(
                    test_name=test_name,
                    success=False,
                    response_time=0,
                    message=f"响应性能测试失败: {str(e)}",
                    details={"script": script, "error": str(e)}
                ))
        
        return results
    
    async def _test_memory_usage(self) -> List[TestResult]:
        """测试内存使用"""
        results = []
        
        try:
            import psutil
            
            # 测试不同CLI脚本的内存使用
            scripts = ["start_cli.py", "ui/cli/modern_cli.py"]
            
            for script in scripts:
                test_name = f"memory_usage_{script.replace('/', '_').replace('.py', '')}"
                
                try:
                    # 启动CLI进程
                    process = subprocess.Popen(
                        [sys.executable, script],
                        cwd=str(project_root),
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # 等待进程稳定
                    await asyncio.sleep(2)
                    
                    # 测量内存使用
                    if process.poll() is None:  # 进程仍在运行
                        ps_process = psutil.Process(process.pid)
                        memory_info = ps_process.memory_info()
                        memory_mb = memory_info.rss / 1024 / 1024  # 转换为MB
                        
                        success = memory_mb <= self.performance_benchmarks["memory_usage_threshold"]
                        
                        results.append(TestResult(
                            test_name=test_name,
                            success=success,
                            response_time=0,
                            message=f"内存使用: {memory_mb:.1f}MB",
                            details={
                                "script": script,
                                "memory_mb": memory_mb,
                                "memory_bytes": memory_info.rss,
                                "threshold_mb": self.performance_benchmarks["memory_usage_threshold"]
                            }
                        ))
                    else:
                        results.append(TestResult(
                            test_name=test_name,
                            success=False,
                            response_time=0,
                            message=f"进程 {script} 提前退出",
                            details={"script": script, "error": "process_exited_early"}
                        ))
                    
                    # 清理进程
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                
                except Exception as e:
                    results.append(TestResult(
                        test_name=test_name,
                        success=False,
                        response_time=0,
                        message=f"内存使用测试失败: {str(e)}",
                        details={"script": script, "error": str(e)}
                    ))
        
        except ImportError:
            results.append(TestResult(
                test_name="memory_usage_psutil_missing",
                success=False,
                response_time=0,
                message="psutil模块未安装，无法进行内存使用测试",
                details={"error": "psutil_not_installed"}
            ))
        
        return results
    
    async def _test_concurrent_performance(self) -> List[TestResult]:
        """测试并发性能"""
        results = []
        
        # 模拟多个并发CLI会话
        concurrent_sessions = [2, 4, 8]
        
        for session_count in concurrent_sessions:
            test_name = f"concurrent_performance_{session_count}_sessions"
            start_time = time.time()
            
            try:
                # 创建多个并发任务
                tasks = []
                for i in range(session_count):
                    task = self.run_cli_command(
                        "python start_cli.py",
                        [f"测试会话{i}", "exit"],
                        timeout=15
                    )
                    tasks.append(task)
                
                # 等待所有任务完成
                results_list = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # 分析结果
                successful_sessions = sum(1 for r in results_list if isinstance(r, dict) and r.get("success", False))
                success_rate = successful_sessions / session_count
                
                success = success_rate >= 0.8  # 80%以上成功率认为通过
                
                results.append(TestResult(
                    test_name=test_name,
                    success=success,
                    response_time=total_time,
                    message=f"并发{session_count}会话: {successful_sessions}/{session_count}成功",
                    details={
                        "session_count": session_count,
                        "successful_sessions": successful_sessions,
                        "success_rate": success_rate,
                        "total_time": total_time,
                        "avg_time_per_session": total_time / session_count,
                        "results": [r if not isinstance(r, Exception) else str(r) for r in results_list]
                    }
                ))
            
            except Exception as e:
                results.append(TestResult(
                    test_name=test_name,
                    success=False,
                    response_time=time.time() - start_time,
                    message=f"并发性能测试失败: {str(e)}",
                    details={"session_count": session_count, "error": str(e)}
                ))
        
        return results


class CLICompatibilityTestSuite(CLICompatibilityTest):
    """CLI兼容性测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
    
    async def run_compatibility_tests(self):
        """运行兼容性测试"""
        print("🔄 开始CLI兼容性测试")
        
        await self.setup_test_environment()
        
        try:
            # Python版本兼容性测试
            python_results = await self._test_python_compatibility()
            self.test_results.extend(python_results)
            
            # 终端兼容性测试
            terminal_results = await self._test_terminal_compatibility_extended()
            self.test_results.extend(terminal_results)
            
            # 操作系统兼容性测试
            os_results = await self._test_os_compatibility()
            self.test_results.extend(os_results)
            
            # 字符编码兼容性测试
            encoding_results = await self._test_encoding_compatibility()
            self.test_results.extend(encoding_results)
            
        finally:
            await self.teardown_test_environment()
    
    async def _test_python_compatibility(self) -> List[TestResult]:
        """测试Python兼容性"""
        results = []
        
        test_name = "python_version_compatibility"
        start_time = time.time()
        
        try:
            compat_result = await self.test_python_version_compatibility()
            
            success = compat_result["overall_compatible"]
            
            results.append(TestResult(
                test_name=test_name,
                success=success,
                response_time=time.time() - start_time,
                message=f"Python {compat_result['python_version']} 兼容性: {'通过' if success else '失败'}",
                details=compat_result
            ))
        
        except Exception as e:
            results.append(TestResult(
                test_name=test_name,
                success=False,
                response_time=time.time() - start_time,
                message=f"Python兼容性测试失败: {str(e)}",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _test_terminal_compatibility_extended(self) -> List[TestResult]:
        """扩展终端兼容性测试"""
        results = []
        
        try:
            compat_result = await self.test_terminal_compatibility()
            
            for term_config, result in compat_result.items():
                test_name = f"terminal_compatibility_{term_config}"
                
                success = result.get("success", False)
                config = result.get("config", {})
                
                results.append(TestResult(
                    test_name=test_name,
                    success=success,
                    response_time=0,
                    message=f"终端 {config.get('TERM', 'unknown')} 兼容性: {'通过' if success else '失败'}",
                    details=result
                ))
        
        except Exception as e:
            results.append(TestResult(
                test_name="terminal_compatibility_error",
                success=False,
                response_time=0,
                message=f"终端兼容性测试失败: {str(e)}",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _test_os_compatibility(self) -> List[TestResult]:
        """测试操作系统兼容性"""
        results = []
        
        test_name = "os_compatibility"
        start_time = time.time()
        
        try:
            # 获取系统信息
            system_info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
            
            # 测试路径处理
            path_test_success = True
            try:
                test_path = Path(self.temp_dir) / "test_file.txt"
                test_path.write_text("测试内容")
                content = test_path.read_text()
                test_path.unlink()
                path_test_success = content == "测试内容"
            except Exception:
                path_test_success = False
            
            # 测试进程管理
            process_test_success = True
            try:
                proc = subprocess.Popen([sys.executable, "--version"], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate(timeout=5)
                process_test_success = proc.returncode == 0
            except Exception:
                process_test_success = False
            
            # 综合评估
            success = path_test_success and process_test_success
            
            results.append(TestResult(
                test_name=test_name,
                success=success,
                response_time=time.time() - start_time,
                message=f"操作系统 {system_info['system']} 兼容性: {'通过' if success else '失败'}",
                details={
                    "system_info": system_info,
                    "path_test": path_test_success,
                    "process_test": process_test_success
                }
            ))
        
        except Exception as e:
            results.append(TestResult(
                test_name=test_name,
                success=False,
                response_time=time.time() - start_time,
                message=f"操作系统兼容性测试失败: {str(e)}",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _test_encoding_compatibility(self) -> List[TestResult]:
        """测试字符编码兼容性"""
        results = []
        
        # 测试不同的字符编码
        encoding_tests = [
            {"name": "utf8", "text": "你好世界 Hello World! 🚀"},
            {"name": "ascii", "text": "Hello World"},
            {"name": "emoji", "text": "🤖 AI助手 💬 对话 ⚡ 性能"},
            {"name": "special_chars", "text": "特殊字符: !@#$%^&*()"},
            {"name": "multiline", "text": "第一行\n第二行\n第三行"}
        ]
        
        for test in encoding_tests:
            test_name = f"encoding_compatibility_{test['name']}"
            start_time = time.time()
            
            try:
                # 测试CLI能否正确处理这些字符
                result = await self.run_cli_command(
                    "python start_cli.py",
                    [test["text"], "exit"],
                    timeout=10
                )
                
                # 检查是否有编码错误
                has_encoding_error = (
                    "UnicodeDecodeError" in result["stderr"] or
                    "UnicodeEncodeError" in result["stderr"] or
                    "encoding" in result["stderr"].lower()
                )
                
                success = result["success"] and not has_encoding_error
                
                results.append(TestResult(
                    test_name=test_name,
                    success=success,
                    response_time=time.time() - start_time,
                    message=f"编码测试 {test['name']}: {'通过' if success else '失败'}",
                    details={
                        "test_text": test["text"],
                        "command_result": result,
                        "has_encoding_error": has_encoding_error
                    }
                ))
            
            except Exception as e:
                results.append(TestResult(
                    test_name=test_name,
                    success=False,
                    response_time=time.time() - start_time,
                    message=f"编码兼容性测试失败: {str(e)}",
                    details={"test_text": test["text"], "error": str(e)}
                ))
        
        return results


# 运行测试的主函数
async def main():
    """主测试函数"""
    print("🧪 开始CLI性能和兼容性测试")
    print("=" * 60)
    
    # 性能测试
    performance_suite = CLIPerformanceTestSuite()
    await performance_suite.run_performance_tests()
    performance_report = performance_suite.generate_test_report()
    
    # 兼容性测试
    compatibility_suite = CLICompatibilityTestSuite()
    await compatibility_suite.run_compatibility_tests()
    compatibility_report = compatibility_suite.generate_test_report()
    
    # 打印报告
    print("\n" + "="*60)
    print("CLI性能测试报告:")
    print(f"总测试数: {performance_report['summary']['total_tests']}")
    print(f"通过: {performance_report['summary']['passed']}")
    print(f"失败: {performance_report['summary']['failed']}")
    print(f"成功率: {performance_report['summary']['success_rate']}")
    
    print("\nCLI兼容性测试报告:")
    print(f"总测试数: {compatibility_report['summary']['total_tests']}")
    print(f"通过: {compatibility_report['summary']['passed']}")
    print(f"失败: {compatibility_report['summary']['failed']}")
    print(f"成功率: {compatibility_report['summary']['success_rate']}")
    
    # 保存详细报告
    test_reports_dir = Path("test_reports")
    test_reports_dir.mkdir(exist_ok=True)
    
    with open(test_reports_dir / "cli_performance_report.json", "w", encoding="utf-8") as f:
        json.dump(performance_report, f, ensure_ascii=False, indent=2)
    
    with open(test_reports_dir / "cli_compatibility_report.json", "w", encoding="utf-8") as f:
        json.dump(compatibility_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存到 {test_reports_dir}")


if __name__ == "__main__":
    asyncio.run(main())