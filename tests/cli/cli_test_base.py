#!/usr/bin/env python3
"""
CLI测试基础框架
提供CLI组件的测试基础设施和工具
"""
import asyncio
import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import patch, MagicMock, AsyncMock
import time

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.base import BaseTestSuite, TestResult
from ui.shared.ai_client import EnhancedAIClient


class CLITestBase(BaseTestSuite):
    """CLI测试基础类"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.cli_root = project_root / "ui" / "cli"
        self.temp_dir = None
        self.cli_process = None
        
    async def setup_test_environment(self):
        """设置测试环境"""
        await super().setup_test_environment()
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="cli_test_")
        
        # 设置环境变量
        os.environ["CLI_TEST_MODE"] = "true"
        os.environ["CLI_TEST_DATA_DIR"] = self.temp_dir
        
    async def teardown_test_environment(self):
        """清理测试环境"""
        # 清理进程
        if self.cli_process and self.cli_process.poll() is None:
            self.cli_process.terminate()
            try:
                self.cli_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.cli_process.kill()
        
        # 清理临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # 清理环境变量
        os.environ.pop("CLI_TEST_MODE", None)
        os.environ.pop("CLI_TEST_DATA_DIR", None)
        
        await super().teardown_test_environment()
    
    def mock_user_input(self, inputs: List[str]) -> MagicMock:
        """模拟用户输入"""
        mock_input = MagicMock(side_effect=inputs)
        return mock_input
    
    def mock_console_output(self) -> Tuple[MagicMock, List[str]]:
        """模拟控制台输出"""
        output_buffer = []
        
        def capture_print(*args, **kwargs):
            output_buffer.append(" ".join(str(arg) for arg in args))
        
        mock_print = MagicMock(side_effect=capture_print)
        return mock_print, output_buffer
    
    async def run_cli_command(self, command: str, inputs: Optional[List[str]] = None, 
                             timeout: int = 10) -> Dict[str, Any]:
        """运行CLI命令并返回结果"""
        try:
            # 准备命令
            if command.startswith("python"):
                cmd = [sys.executable] + command.split()[1:]
            else:
                cmd = command.split()
            
            # 准备输入
            input_text = "\n".join(inputs) + "\n" if inputs else ""
            
            # 运行命令
            process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONPATH": str(project_root)}
            )
            
            try:
                stdout, stderr = process.communicate(input=input_text, timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return_code = -1
            
            return {
                "return_code": return_code,
                "stdout": stdout,
                "stderr": stderr,
                "success": return_code == 0,
                "command": command
            }
            
        except Exception as e:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "command": command,
                "error": str(e)
            }
    
    async def test_cli_component(self, component_name: str, test_cases: List[Dict]) -> List[TestResult]:
        """测试CLI组件"""
        results = []
        
        for i, test_case in enumerate(test_cases):
            test_name = f"{component_name}_{test_case.get('name', f'test_{i+1}')}"
            start_time = time.time()
            
            try:
                # 运行测试用例
                result = await self._execute_cli_test_case(component_name, test_case)
                
                # 验证结果
                success = self._validate_cli_test_result(test_case, result)
                
                test_result = TestResult(
                    test_name=test_name,
                    success=success,
                    response_time=time.time() - start_time,
                    message=result.get("message", ""),
                    details=result
                )
                
            except Exception as e:
                test_result = TestResult(
                    test_name=test_name,
                    success=False,
                    response_time=time.time() - start_time,
                    message=f"测试执行异常: {str(e)}",
                    details={"error": str(e)}
                )
            
            results.append(test_result)
        
        return results
    
    async def _execute_cli_test_case(self, component_name: str, test_case: Dict) -> Dict[str, Any]:
        """执行单个CLI测试用例"""
        test_type = test_case.get("type", "command")
        
        if test_type == "command":
            return await self._test_command_execution(test_case)
        elif test_type == "interaction":
            return await self._test_user_interaction(test_case)
        elif test_type == "display":
            return await self._test_display_rendering(test_case)
        elif test_type == "session":
            return await self._test_session_management(test_case)
        else:
            raise ValueError(f"不支持的测试类型: {test_type}")
    
    async def _test_command_execution(self, test_case: Dict) -> Dict[str, Any]:
        """测试命令执行"""
        command = test_case.get("command", "")
        inputs = test_case.get("inputs", [])
        expected_patterns = test_case.get("expected_patterns", [])
        
        result = await self.run_cli_command(command, inputs)
        
        # 检查输出模式
        pattern_matches = []
        for pattern in expected_patterns:
            if pattern in result["stdout"] or pattern in result["stderr"]:
                pattern_matches.append({"pattern": pattern, "found": True})
            else:
                pattern_matches.append({"pattern": pattern, "found": False})
        
        return {
            "command_result": result,
            "pattern_matches": pattern_matches,
            "message": f"命令执行: {command}"
        }
    
    async def _test_user_interaction(self, test_case: Dict) -> Dict[str, Any]:
        """测试用户交互"""
        # 这里需要模拟用户交互流程
        script_path = test_case.get("script_path", "start_cli.py")
        user_inputs = test_case.get("user_inputs", [])
        expected_responses = test_case.get("expected_responses", [])
        
        # 运行交互式CLI
        command = f"python {script_path}"
        result = await self.run_cli_command(command, user_inputs, timeout=30)
        
        # 分析交互结果
        response_matches = []
        for expected_response in expected_responses:
            if expected_response in result["stdout"]:
                response_matches.append({"expected": expected_response, "found": True})
            else:
                response_matches.append({"expected": expected_response, "found": False})
        
        return {
            "interaction_result": result,
            "response_matches": response_matches,
            "message": "用户交互测试"
        }
    
    async def _test_display_rendering(self, test_case: Dict) -> Dict[str, Any]:
        """测试显示渲染"""
        # 模拟Rich/Textual组件的渲染测试
        component_name = test_case.get("component", "")
        test_data = test_case.get("test_data", {})
        
        # 这里需要导入并测试特定的显示组件
        try:
            if component_name == "display_engine":
                from ui.cli.display_engine import DisplayEngine
                from rich.console import Console
                
                console = Console(file=sys.stdout, force_terminal=False)
                display_engine = DisplayEngine(console)
                
                # 测试不同的显示方法
                if test_data.get("test_method") == "show_user_message":
                    display_engine.show_user_message(test_data.get("message", "测试消息"))
                elif test_data.get("test_method") == "show_ai_response":
                    display_engine.show_ai_response(test_data.get("response", "测试响应"))
                
                return {
                    "component": component_name,
                    "test_data": test_data,
                    "success": True,
                    "message": "显示组件渲染成功"
                }
            
        except Exception as e:
            return {
                "component": component_name,
                "test_data": test_data,
                "success": False,
                "error": str(e),
                "message": f"显示组件渲染失败: {e}"
            }
        
        return {
            "component": component_name,
            "message": "显示组件测试完成"
        }
    
    async def _test_session_management(self, test_case: Dict) -> Dict[str, Any]:
        """测试会话管理"""
        operation = test_case.get("operation", "create")
        session_data = test_case.get("session_data", {})
        
        try:
            if operation == "create":
                # 测试会话创建
                from ui.cli.session_manager import SessionManager
                session_manager = SessionManager()
                await session_manager.initialize()
                
                session_info = await session_manager.create_session(session_data)
                
                return {
                    "operation": operation,
                    "session_info": session_info,
                    "success": True,
                    "message": "会话创建成功"
                }
            
        except Exception as e:
            return {
                "operation": operation,
                "success": False,
                "error": str(e),
                "message": f"会话管理测试失败: {e}"
            }
        
        return {
            "operation": operation,
            "message": "会话管理测试完成"
        }
    
    def _validate_cli_test_result(self, test_case: Dict, result: Dict) -> bool:
        """验证CLI测试结果"""
        expected_success = test_case.get("expected_success", True)
        validation_rules = test_case.get("validation_rules", [])
        
        # 基本成功性检查
        if "success" in result and result["success"] != expected_success:
            return False
        
        # 应用验证规则
        for rule in validation_rules:
            rule_type = rule.get("type", "")
            
            if rule_type == "output_contains":
                expected_text = rule.get("text", "")
                if "command_result" in result:
                    output = result["command_result"].get("stdout", "") + result["command_result"].get("stderr", "")
                    if expected_text not in output:
                        return False
            
            elif rule_type == "pattern_match":
                pattern_matches = result.get("pattern_matches", [])
                expected_patterns = rule.get("patterns", [])
                for pattern in expected_patterns:
                    found = any(match["pattern"] == pattern and match["found"] for match in pattern_matches)
                    if not found:
                        return False
            
            elif rule_type == "return_code":
                expected_code = rule.get("code", 0)
                if "command_result" in result:
                    actual_code = result["command_result"].get("return_code", -1)
                    if actual_code != expected_code:
                        return False
        
        return True


class CLIPerformanceTest(CLITestBase):
    """CLI性能测试"""
    
    async def measure_startup_time(self, script_path: str) -> Dict[str, Any]:
        """测量CLI启动时间"""
        start_time = time.time()
        
        # 运行CLI脚本并立即退出
        result = await self.run_cli_command(f"python {script_path}", ["exit"], timeout=10)
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        return {
            "script_path": script_path,
            "startup_time": startup_time,
            "success": result["success"],
            "details": result
        }
    
    async def measure_response_time(self, script_path: str, test_inputs: List[str]) -> Dict[str, Any]:
        """测量响应时间"""
        response_times = []
        
        for input_command in test_inputs:
            start_time = time.time()
            
            result = await self.run_cli_command(
                f"python {script_path}", 
                [input_command, "exit"], 
                timeout=15
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append({
                "input": input_command,
                "response_time": response_time,
                "success": result["success"]
            })
        
        avg_response_time = sum(rt["response_time"] for rt in response_times) / len(response_times)
        
        return {
            "script_path": script_path,
            "response_times": response_times,
            "average_response_time": avg_response_time,
            "total_tests": len(test_inputs)
        }


class CLICompatibilityTest(CLITestBase):
    """CLI兼容性测试"""
    
    async def test_terminal_compatibility(self) -> Dict[str, Any]:
        """测试终端兼容性"""
        compatibility_results = {}
        
        # 测试不同的终端环境变量设置
        terminal_configs = [
            {"TERM": "xterm", "COLORTERM": ""},
            {"TERM": "xterm-256color", "COLORTERM": "truecolor"},
            {"TERM": "screen", "COLORTERM": ""},
            {"TERM": "linux", "COLORTERM": ""}
        ]
        
        for config in terminal_configs:
            # 保存原始环境变量
            original_env = {}
            for key in config:
                original_env[key] = os.environ.get(key, "")
                os.environ[key] = config[key]
            
            try:
                # 测试CLI在该环境下的运行
                result = await self.run_cli_command("python start_cli.py", ["help", "exit"])
                
                compatibility_results[f"term_{config['TERM']}"] = {
                    "config": config,
                    "success": result["success"],
                    "details": result
                }
                
            except Exception as e:
                compatibility_results[f"term_{config['TERM']}"] = {
                    "config": config,
                    "success": False,
                    "error": str(e)
                }
            
            finally:
                # 恢复原始环境变量
                for key, value in original_env.items():
                    if value:
                        os.environ[key] = value
                    else:
                        os.environ.pop(key, None)
        
        return compatibility_results
    
    async def test_python_version_compatibility(self) -> Dict[str, Any]:
        """测试Python版本兼容性"""
        # 获取当前Python版本信息
        python_version = sys.version_info
        
        # 检查最低版本要求
        min_version = (3, 9)
        version_compatible = python_version >= min_version
        
        # 测试关键模块导入
        import_tests = {}
        critical_modules = [
            "rich", "textual", "asyncio", "aiohttp", 
            "fastapi", "uvicorn", "pydantic"
        ]
        
        for module_name in critical_modules:
            try:
                __import__(module_name)
                import_tests[module_name] = {"success": True, "error": None}
            except ImportError as e:
                import_tests[module_name] = {"success": False, "error": str(e)}
        
        return {
            "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
            "version_compatible": version_compatible,
            "min_version_required": f"{min_version[0]}.{min_version[1]}",
            "import_tests": import_tests,
            "overall_compatible": version_compatible and all(test["success"] for test in import_tests.values())
        }