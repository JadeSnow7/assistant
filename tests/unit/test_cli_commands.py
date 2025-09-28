#!/usr/bin/env python3
"""
CLI命令路由测试
测试命令解析、路由和执行功能
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, AsyncMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.unit.cli_test_base import CLITestBase, TestResult


class CLICommandRoutingTestSuite(CLITestBase):
    """CLI命令路由测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.command_test_cases = [
            # 基础命令测试
            {
                "name": "help_command",
                "type": "command",
                "command": "python ui/cli/modern_cli.py",
                "inputs": ["/help", "/exit"],
                "expected_patterns": ["帮助", "命令", "退出"],
                "validation_rules": [
                    {"type": "return_code", "code": 0},
                    {"type": "output_contains", "text": "help"}
                ],
                "expected_success": True
            },
            {
                "name": "simple_chat",
                "type": "interaction",
                "script_path": "start_cli.py",
                "user_inputs": ["你好", "exit"],
                "expected_responses": ["AI:", "再见"],
                "validation_rules": [
                    {"type": "output_contains", "text": "你好"}
                ],
                "expected_success": True
            },
            {
                "name": "system_commands",
                "type": "command",
                "command": "python ui/cli/modern_cli.py",
                "inputs": ["/status", "/health", "/exit"],
                "expected_patterns": ["status", "health"],
                "validation_rules": [
                    {"type": "return_code", "code": 0}
                ],
                "expected_success": True
            },
            # 错误处理测试
            {
                "name": "invalid_command",
                "type": "command", 
                "command": "python ui/cli/modern_cli.py",
                "inputs": ["/invalid_command", "/exit"],
                "expected_patterns": ["未知", "无效", "错误"],
                "validation_rules": [
                    {"type": "output_contains", "text": "未知"}
                ],
                "expected_success": True
            },
            # 会话管理测试
            {
                "name": "session_persistence",
                "type": "session",
                "operation": "create",
                "session_data": {"user_id": "test_user", "context": "test"},
                "validation_rules": [],
                "expected_success": True
            }
        ]
    
    async def run_command_routing_tests(self):
        """运行命令路由测试"""
        print("🧪 开始CLI命令路由测试")
        
        await self.setup_test_environment()
        
        try:
            # 运行基础命令测试
            basic_results = await self.test_cli_component("command_routing", self.command_test_cases)
            self.test_results.extend(basic_results)
            
            # 运行高级路由测试
            advanced_results = await self._test_advanced_routing()
            self.test_results.extend(advanced_results)
            
            # 运行命令解析测试
            parsing_results = await self._test_command_parsing()
            self.test_results.extend(parsing_results)
            
        finally:
            await self.teardown_test_environment()
    
    async def _test_advanced_routing(self) -> List[TestResult]:
        """测试高级路由功能"""
        results = []
        
        # 测试条件路由
        conditional_tests = [
            {
                "name": "conditional_routing_authenticated",
                "type": "interaction",
                "script_path": "ui/cli/modern_cli.py",
                "user_inputs": ["/login test_user", "/profile", "/exit"],
                "expected_responses": ["登录", "profile"],
                "setup": "authenticated_user"
            },
            {
                "name": "conditional_routing_unauthenticated", 
                "type": "interaction",
                "script_path": "ui/cli/modern_cli.py",
                "user_inputs": ["/profile", "/exit"],
                "expected_responses": ["需要登录", "请先登录"],
                "setup": "unauthenticated_user"
            }
        ]
        
        for test_case in conditional_tests:
            test_result = await self._run_conditional_routing_test(test_case)
            results.append(test_result)
        
        return results
    
    async def _run_conditional_routing_test(self, test_case: Dict) -> TestResult:
        """运行条件路由测试"""
        test_name = test_case["name"]
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 模拟不同的用户状态
            setup = test_case.get("setup", "")
            
            with patch('ui.cli.session_manager.SessionManager') as mock_session:
                if setup == "authenticated_user":
                    mock_session.return_value.get_current_user.return_value = {"id": "test_user", "authenticated": True}
                else:
                    mock_session.return_value.get_current_user.return_value = None
                
                # 执行测试
                result = await self._execute_cli_test_case("advanced_routing", test_case)
                success = self._validate_cli_test_result(test_case, result)
                
                return TestResult(
                    test_name=test_name,
                    success=success,
                    response_time=asyncio.get_event_loop().time() - start_time,
                    message=result.get("message", ""),
                    details=result
                )
        
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                response_time=asyncio.get_event_loop().time() - start_time,
                message=f"高级路由测试失败: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _test_command_parsing(self) -> List[TestResult]:
        """测试命令解析功能"""
        results = []
        
        # 导入命令路由器进行单元测试
        try:
            from ui.cli.command_router import CommandRouter
            
            # 创建模拟的CLI实例
            mock_cli = MagicMock()
            mock_cli.client = AsyncMock()
            
            router = CommandRouter(mock_cli)
            
            # 测试不同的命令解析场景
            parsing_tests = [
                {
                    "input": "/help",
                    "expected_command": "help",
                    "expected_args": []
                },
                {
                    "input": "/chat 你好世界",
                    "expected_command": "chat",
                    "expected_args": ["你好世界"]
                },
                {
                    "input": "/set config key=value",
                    "expected_command": "set",
                    "expected_args": ["config", "key=value"]
                },
                {
                    "input": "普通对话内容",
                    "expected_command": "chat",
                    "expected_args": ["普通对话内容"]
                }
            ]
            
            for i, test in enumerate(parsing_tests):
                test_name = f"command_parsing_{i+1}"
                start_time = asyncio.get_event_loop().time()
                
                try:
                    # 测试命令解析
                    parsed = router._parse_command(test["input"])
                    
                    success = (
                        parsed.get("command") == test["expected_command"] and
                        parsed.get("args", []) == test["expected_args"]
                    )
                    
                    results.append(TestResult(
                        test_name=test_name,
                        success=success,
                        response_time=asyncio.get_event_loop().time() - start_time,
                        message=f"解析命令: {test['input']}",
                        details={
                            "input": test["input"],
                            "parsed": parsed,
                            "expected": {
                                "command": test["expected_command"],
                                "args": test["expected_args"]
                            }
                        }
                    ))
                
                except Exception as e:
                    results.append(TestResult(
                        test_name=test_name,
                        success=False,
                        response_time=asyncio.get_event_loop().time() - start_time,
                        message=f"命令解析异常: {str(e)}",
                        details={"error": str(e), "input": test["input"]}
                    ))
        
        except ImportError as e:
            # 如果无法导入命令路由器，创建一个失败的测试结果
            results.append(TestResult(
                test_name="command_parsing_import",
                success=False,
                response_time=0,
                message=f"无法导入CommandRouter: {str(e)}",
                details={"error": str(e)}
            ))
        
        return results


class CLIDisplayTestSuite(CLITestBase):
    """CLI显示测试套件"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.display_test_cases = [
            {
                "name": "user_message_display",
                "type": "display",
                "component": "display_engine",
                "test_data": {
                    "test_method": "show_user_message",
                    "message": "测试用户消息显示"
                },
                "expected_success": True
            },
            {
                "name": "ai_response_display",
                "type": "display",
                "component": "display_engine", 
                "test_data": {
                    "test_method": "show_ai_response",
                    "response": "测试AI响应显示"
                },
                "expected_success": True
            },
            {
                "name": "streaming_display",
                "type": "display",
                "component": "streaming_display",
                "test_data": {
                    "test_method": "stream_response",
                    "content": "这是一个流式响应测试",
                    "chunks": ["这是", "一个", "流式", "响应", "测试"]
                },
                "expected_success": True
            }
        ]
    
    async def run_display_tests(self):
        """运行显示测试"""
        print("🎨 开始CLI显示测试")
        
        await self.setup_test_environment()
        
        try:
            # 运行基础显示测试
            display_results = await self.test_cli_component("display", self.display_test_cases)
            self.test_results.extend(display_results)
            
            # 运行Rich组件测试
            rich_results = await self._test_rich_components()
            self.test_results.extend(rich_results)
            
            # 运行响应式布局测试
            layout_results = await self._test_responsive_layout()
            self.test_results.extend(layout_results)
            
        finally:
            await self.teardown_test_environment()
    
    async def _test_rich_components(self) -> List[TestResult]:
        """测试Rich组件"""
        results = []
        
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            from rich.progress import Progress
            import io
            
            # 创建字符串缓冲区来捕获输出
            string_buffer = io.StringIO()
            console = Console(file=string_buffer, force_terminal=False, width=80)
            
            # 测试不同的Rich组件
            component_tests = [
                {
                    "name": "panel_rendering",
                    "component": lambda: Panel("测试面板内容", title="测试面板"),
                    "expected_content": ["测试面板", "测试面板内容"]
                },
                {
                    "name": "table_rendering", 
                    "component": lambda: self._create_test_table(),
                    "expected_content": ["列1", "列2", "数据1", "数据2"]
                },
                {
                    "name": "progress_rendering",
                    "component": lambda: self._create_test_progress(),
                    "expected_content": ["进度", "%"]
                }
            ]
            
            for test in component_tests:
                test_name = f"rich_{test['name']}"
                start_time = asyncio.get_event_loop().time()
                
                try:
                    # 清空缓冲区
                    string_buffer.seek(0)
                    string_buffer.truncate(0)
                    
                    # 渲染组件
                    component = test["component"]()
                    console.print(component)
                    
                    # 获取输出
                    output = string_buffer.getvalue()
                    
                    # 检查预期内容
                    success = all(content in output for content in test["expected_content"])
                    
                    results.append(TestResult(
                        test_name=test_name,
                        success=success,
                        response_time=asyncio.get_event_loop().time() - start_time,
                        message=f"Rich组件渲染: {test['name']}",
                        details={
                            "output_length": len(output),
                            "expected_content": test["expected_content"],
                            "content_found": [content for content in test["expected_content"] if content in output]
                        }
                    ))
                
                except Exception as e:
                    results.append(TestResult(
                        test_name=test_name,
                        success=False,
                        response_time=asyncio.get_event_loop().time() - start_time,
                        message=f"Rich组件渲染失败: {str(e)}",
                        details={"error": str(e)}
                    ))
        
        except ImportError as e:
            results.append(TestResult(
                test_name="rich_import",
                success=False,
                response_time=0,
                message=f"无法导入Rich模块: {str(e)}",
                details={"error": str(e)}
            ))
        
        return results
    
    def _create_test_table(self):
        """创建测试表格"""
        from rich.table import Table
        
        table = Table(title="测试表格")
        table.add_column("列1", style="cyan")
        table.add_column("列2", style="magenta")
        table.add_row("数据1", "数据2")
        table.add_row("数据3", "数据4")
        
        return table
    
    def _create_test_progress(self):
        """创建测试进度条"""
        from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
        
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        
        task = progress.add_task("测试进度", total=100)
        progress.update(task, advance=50)
        
        return progress
    
    async def _test_responsive_layout(self) -> List[TestResult]:
        """测试响应式布局"""
        results = []
        
        # 测试不同终端宽度下的布局
        terminal_widths = [40, 80, 120, 160]
        
        for width in terminal_widths:
            test_name = f"responsive_layout_width_{width}"
            start_time = asyncio.get_event_loop().time()
            
            try:
                from rich.console import Console
                from rich.layout import Layout
                import io
                
                string_buffer = io.StringIO()
                console = Console(file=string_buffer, force_terminal=False, width=width)
                
                # 创建响应式布局
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="body"),
                    Layout(name="footer", size=3)
                )
                
                layout["header"].update("头部内容")
                layout["body"].update("主体内容 " * 20)  # 长内容测试换行
                layout["footer"].update("底部内容")
                
                console.print(layout)
                output = string_buffer.getvalue()
                
                # 检查布局是否正确适应宽度
                lines = output.split('\n')
                max_line_length = max(len(line.rstrip()) for line in lines if line.strip())
                
                success = max_line_length <= width
                
                results.append(TestResult(
                    test_name=test_name,
                    success=success,
                    response_time=asyncio.get_event_loop().time() - start_time,
                    message=f"响应式布局测试 (宽度: {width})",
                    details={
                        "terminal_width": width,
                        "max_line_length": max_line_length,
                        "total_lines": len(lines),
                        "layout_fits": success
                    }
                ))
            
            except Exception as e:
                results.append(TestResult(
                    test_name=test_name,
                    success=False,
                    response_time=asyncio.get_event_loop().time() - start_time,
                    message=f"响应式布局测试失败: {str(e)}",
                    details={"error": str(e), "width": width}
                ))
        
        return results


# 运行测试的主函数
async def main():
    """主测试函数"""
    # 命令路由测试
    routing_suite = CLICommandRoutingTestSuite()
    await routing_suite.run_command_routing_tests()
    routing_report = routing_suite.generate_test_report()
    
    # 显示测试
    display_suite = CLIDisplayTestSuite()
    await display_suite.run_display_tests()
    display_report = display_suite.generate_test_report()
    
    # 打印报告
    print("\n" + "="*60)
    print("CLI命令路由测试报告:")
    print(f"总测试数: {routing_report['summary']['total_tests']}")
    print(f"通过: {routing_report['summary']['passed']}")
    print(f"失败: {routing_report['summary']['failed']}")
    print(f"成功率: {routing_report['summary']['success_rate']}")
    
    print("\nCLI显示测试报告:")
    print(f"总测试数: {display_report['summary']['total_tests']}")
    print(f"通过: {display_report['summary']['passed']}")
    print(f"失败: {display_report['summary']['failed']}")
    print(f"成功率: {display_report['summary']['success_rate']}")


if __name__ == "__main__":
    asyncio.run(main())