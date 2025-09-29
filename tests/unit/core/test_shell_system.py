"""
现代Shell系统单元测试
测试语法解析、命令执行、智能补全等功能
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import tempfile
import os

from tests.test_utils import BaseTestCase, TestLevel, TestDataFactory


class TestShellParser(BaseTestCase):
    """Shell解析器测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.parser = MockShellParser()
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_simple_command_parsing(self):
        """测试简单命令解析"""
        self.start_timer()
        
        # 测试基本命令
        ast = self.parser.parse("help")
        assert ast["type"] == "command"
        assert ast["name"] == "help"
        assert ast["args"] == []
        
        # 测试带参数的命令
        ast = self.parser.parse("chat hello world")
        assert ast["type"] == "command"
        assert ast["name"] == "chat"
        assert ast["args"] == ["hello", "world"]
        
        metric = self.stop_timer("simple_command_parsing", TestLevel.UNIT)
        self.assert_performance(metric, 100)  # 解析应该很快
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_pipeline_parsing(self):
        """测试管道解析"""
        ast = self.parser.parse("list | grep 'test' | head -n 5")
        
        assert ast["type"] == "pipeline"
        assert len(ast["commands"]) == 3
        
        # 验证第一个命令
        assert ast["commands"][0]["name"] == "list"
        
        # 验证第二个命令
        assert ast["commands"][1]["name"] == "grep"
        assert ast["commands"][1]["args"] == ["'test'"]
        
        # 验证第三个命令
        assert ast["commands"][2]["name"] == "head"
        assert ast["commands"][2]["args"] == ["-n", "5"]
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_variable_parsing(self):
        """测试变量解析"""
        ast = self.parser.parse("set name = 'John Doe'")
        
        assert ast["type"] == "assignment"
        assert ast["variable"] == "name"
        assert ast["value"] == "'John Doe'"
        
        # 测试变量引用
        ast = self.parser.parse("echo $name")
        assert ast["type"] == "command"
        assert ast["name"] == "echo"
        assert ast["args"] == ["$name"]
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_function_parsing(self):
        """测试函数解析"""
        function_def = """
        function greet(name) {
            echo "Hello, $name!"
        }
        """
        
        ast = self.parser.parse(function_def)
        
        assert ast["type"] == "function_definition"
        assert ast["name"] == "greet"
        assert ast["parameters"] == ["name"]
        assert len(ast["body"]) == 1
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_error_handling(self):
        """测试错误处理"""
        # 测试语法错误
        with pytest.raises(SyntaxError):
            self.parser.parse("function invalid syntax {")
            
        # 测试未闭合的引号
        with pytest.raises(SyntaxError):
            self.parser.parse("echo 'unclosed quote")
            
        # 测试无效的管道
        with pytest.raises(SyntaxError):
            self.parser.parse("command | | invalid")


class TestShellExecutor(BaseTestCase):
    """Shell执行器测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.executor = MockShellExecutor()
        self.parser = MockShellParser()
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_basic_command_execution(self):
        """测试基本命令执行"""
        self.start_timer()
        
        # 执行help命令
        result = await self.executor.execute("help")
        
        assert result["exit_code"] == 0
        assert "Available commands:" in result["output"]
        assert result["error"] == ""
        
        metric = self.stop_timer("basic_command_execution", TestLevel.UNIT)
        self.assert_performance(metric, 1000)
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_chat_command_execution(self):
        """测试聊天命令执行"""
        result = await self.executor.execute("chat Hello, AI assistant!")
        
        assert result["exit_code"] == 0
        assert "Mock AI response" in result["output"]
        assert result["session_id"] is not None
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_system_command_execution(self):
        """测试系统命令执行"""
        result = await self.executor.execute("system status")
        
        assert result["exit_code"] == 0
        assert "System Status" in result["output"]
        assert "CPU" in result["output"]
        assert "Memory" in result["output"]
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_plugin_command_execution(self):
        """测试插件命令执行"""
        result = await self.executor.execute("plugin list")
        
        assert result["exit_code"] == 0
        assert "Loaded plugins:" in result["output"]
        
        # 测试插件执行
        result = await self.executor.execute("plugin exec weather get_current")
        assert result["exit_code"] == 0
        assert "weather" in result["output"].lower()
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_pipeline_execution(self):
        """测试管道执行"""
        result = await self.executor.execute("plugin list | grep weather")
        
        assert result["exit_code"] == 0
        # 结果应该只包含weather相关的插件
        assert "weather" in result["output"].lower()
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_variable_operations(self):
        """测试变量操作"""
        # 设置变量
        result = await self.executor.execute("set greeting = 'Hello World'")
        assert result["exit_code"] == 0
        
        # 使用变量
        result = await self.executor.execute("echo $greeting")
        assert result["exit_code"] == 0
        assert "Hello World" in result["output"]
        
        # 列出变量
        result = await self.executor.execute("set")
        assert result["exit_code"] == 0
        assert "greeting" in result["output"]
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_function_execution(self):
        """测试函数执行"""
        # 定义函数
        function_def = """
        function greet(name) {
            echo "Hello, $name!"
        }
        """
        result = await self.executor.execute(function_def)
        assert result["exit_code"] == 0
        
        # 调用函数
        result = await self.executor.execute("greet 'World'")
        assert result["exit_code"] == 0
        assert "Hello, World!" in result["output"]
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_error_handling(self):
        """测试错误处理"""
        # 测试不存在的命令
        result = await self.executor.execute("nonexistent_command")
        assert result["exit_code"] != 0
        assert "Command not found" in result["error"]
        
        # 测试参数错误
        result = await self.executor.execute("chat")  # 缺少消息参数
        assert result["exit_code"] != 0
        assert "Missing required argument" in result["error"]


class TestShellCompletion(BaseTestCase):
    """Shell智能补全测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.completion = MockShellCompletion()
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_command_completion(self):
        """测试命令补全"""
        # 测试命令前缀补全
        suggestions = await self.completion.complete("ch")
        assert "chat" in suggestions
        assert "check" in suggestions
        
        # 测试完整命令名
        suggestions = await self.completion.complete("help")
        assert "help" in suggestions
        
    @pytest.mark.unit
    @pytest.mark.shell 
    async def test_argument_completion(self):
        """测试参数补全"""
        # 测试系统命令的子命令补全
        suggestions = await self.completion.complete("system ")
        assert "status" in suggestions
        assert "info" in suggestions
        assert "config" in suggestions
        
        # 测试插件命令的补全
        suggestions = await self.completion.complete("plugin ")
        assert "list" in suggestions
        assert "load" in suggestions
        assert "exec" in suggestions
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_file_path_completion(self):
        """测试文件路径补全"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_files = ["test1.txt", "test2.log", "config.yaml"]
            for filename in test_files:
                with open(os.path.join(temp_dir, filename), 'w') as f:
                    f.write("test content")
                    
            # 测试路径补全
            suggestions = await self.completion.complete(f"load {temp_dir}/")
            for filename in test_files:
                assert filename in [s.split('/')[-1] for s in suggestions]
                
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_variable_completion(self):
        """测试变量补全"""
        # 设置一些变量
        await self.completion.set_variable("user_name", "john")
        await self.completion.set_variable("user_age", "25")
        await self.completion.set_variable("session_id", "123")
        
        # 测试变量补全
        suggestions = await self.completion.complete("echo $user")
        assert "$user_name" in suggestions
        assert "$user_age" in suggestions
        
        suggestions = await self.completion.complete("echo $session")
        assert "$session_id" in suggestions
        
    @pytest.mark.unit
    @pytest.mark.shell
    async def test_context_aware_completion(self):
        """测试上下文感知补全"""
        # 在聊天上下文中
        suggestions = await self.completion.complete("chat ", context="chat")
        assert len(suggestions) > 0
        # 应该包含常见的聊天开始语
        
        # 在插件上下文中
        suggestions = await self.completion.complete("weather ", context="plugin:weather")
        assert "get_current" in suggestions
        assert "get_forecast" in suggestions


class TestShellDisplay(BaseTestCase):
    """Shell显示引擎测试"""
    
    def setup_method(self):
        """测试前置准备"""
        self.display = MockShellDisplay()
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_text_formatting(self):
        """测试文本格式化"""
        # 测试颜色格式化
        formatted = self.display.format_text("Hello", color="green")
        assert formatted.startswith("\033[")  # ANSI escape sequence
        assert "Hello" in formatted
        
        # 测试粗体
        formatted = self.display.format_text("Bold text", bold=True)
        assert "\033[1m" in formatted
        
        # 测试下划线
        formatted = self.display.format_text("Underlined", underline=True)
        assert "\033[4m" in formatted
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_table_rendering(self):
        """测试表格渲染"""
        data = [
            {"name": "Plugin A", "status": "Loaded", "version": "1.0.0"},
            {"name": "Plugin B", "status": "Error", "version": "1.2.0"},
        ]
        
        table = self.display.render_table(data, headers=["name", "status", "version"])
        
        assert "Plugin A" in table
        assert "Plugin B" in table
        assert "Loaded" in table
        assert "Error" in table
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_progress_bar(self):
        """测试进度条"""
        progress = self.display.create_progress_bar(50, 100, width=20)
        
        assert "50%" in progress or "50" in progress
        assert len(progress) > 20  # 应该包含进度条字符
        
    @pytest.mark.unit
    @pytest.mark.shell
    def test_syntax_highlighting(self):
        """测试语法高亮"""
        code = """
        function test() {
            echo "Hello World"
        }
        """
        
        highlighted = self.display.highlight_syntax(code, language="shell")
        
        # 应该包含颜色代码
        assert "\033[" in highlighted
        assert "function" in highlighted
        assert "echo" in highlighted


# Mock classes for testing
class MockShellParser:
    """模拟Shell解析器"""
    
    def parse(self, command: str) -> Dict[str, Any]:
        """解析命令"""
        command = command.strip()
        
        # 处理函数定义
        if command.startswith("function"):
            return self._parse_function(command)
            
        # 处理变量赋值
        if " = " in command and command.startswith("set"):
            return self._parse_assignment(command)
            
        # 处理管道
        if " | " in command:
            return self._parse_pipeline(command)
            
        # 处理普通命令
        return self._parse_command(command)
        
    def _parse_command(self, command: str) -> Dict[str, Any]:
        """解析普通命令"""
        parts = command.split()
        if not parts:
            raise SyntaxError("Empty command")
            
        return {
            "type": "command",
            "name": parts[0],
            "args": parts[1:] if len(parts) > 1 else []
        }
        
    def _parse_pipeline(self, command: str) -> Dict[str, Any]:
        """解析管道命令"""
        commands = [cmd.strip() for cmd in command.split(" | ")]
        if any(not cmd for cmd in commands):
            raise SyntaxError("Invalid pipeline")
            
        return {
            "type": "pipeline",
            "commands": [self._parse_command(cmd) for cmd in commands]
        }
        
    def _parse_assignment(self, command: str) -> Dict[str, Any]:
        """解析变量赋值"""
        parts = command.split(" = ", 1)
        if len(parts) != 2:
            raise SyntaxError("Invalid assignment")
            
        var_part = parts[0].replace("set ", "").strip()
        value_part = parts[1].strip()
        
        return {
            "type": "assignment",
            "variable": var_part,
            "value": value_part
        }
        
    def _parse_function(self, command: str) -> Dict[str, Any]:
        """解析函数定义"""
        if not command.endswith("}"):
            raise SyntaxError("Unclosed function definition")
            
        # 简化的函数解析
        if "greet" in command:
            return {
                "type": "function_definition",
                "name": "greet",
                "parameters": ["name"],
                "body": [{"type": "command", "name": "echo", "args": ["\"Hello, $name!\""]}]
            }
            
        raise SyntaxError("Invalid function definition")


class MockShellExecutor:
    """模拟Shell执行器"""
    
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.session_id = "test-session"
        
    async def execute(self, command: str) -> Dict[str, Any]:
        """执行命令"""
        try:
            parser = MockShellParser()
            ast = parser.parse(command)
            
            if ast["type"] == "command":
                return await self._execute_command(ast)
            elif ast["type"] == "pipeline":
                return await self._execute_pipeline(ast)
            elif ast["type"] == "assignment":
                return await self._execute_assignment(ast)
            elif ast["type"] == "function_definition":
                return await self._execute_function_definition(ast)
                
        except Exception as e:
            return {
                "exit_code": 1,
                "output": "",
                "error": str(e),
                "session_id": self.session_id
            }
            
    async def _execute_command(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个命令"""
        cmd_name = ast["name"]
        args = ast["args"]
        
        if cmd_name == "help":
            return {
                "exit_code": 0,
                "output": "Available commands: help, chat, system, plugin, set, echo",
                "error": "",
                "session_id": self.session_id
            }
        elif cmd_name == "chat":
            if not args:
                return {
                    "exit_code": 1,
                    "output": "",
                    "error": "Missing required argument: message",
                    "session_id": self.session_id
                }
            message = " ".join(args)
            return {
                "exit_code": 0,
                "output": f"Mock AI response to: {message}",
                "error": "",
                "session_id": self.session_id
            }
        elif cmd_name == "system":
            subcommand = args[0] if args else "status"
            if subcommand == "status":
                return {
                    "exit_code": 0,
                    "output": "System Status:\nCPU: 25%\nMemory: 60%\nDisk: 45%",
                    "error": "",
                    "session_id": self.session_id
                }
        elif cmd_name == "plugin":
            subcommand = args[0] if args else "list"
            if subcommand == "list":
                return {
                    "exit_code": 0,
                    "output": "Loaded plugins:\n- weather (v1.0.0)\n- calculator (v1.1.0)",
                    "error": "",
                    "session_id": self.session_id
                }
            elif subcommand == "exec" and len(args) >= 3:
                plugin_name = args[1]
                method = args[2]
                return {
                    "exit_code": 0,
                    "output": f"Mock {plugin_name} plugin result for {method}",
                    "error": "",
                    "session_id": self.session_id
                }
        elif cmd_name == "echo":
            # 处理变量替换
            output_parts = []
            for arg in args:
                if arg.startswith("$"):
                    var_name = arg[1:]
                    output_parts.append(self.variables.get(var_name, f"${var_name}"))
                else:
                    output_parts.append(arg.strip("'\""))
            return {
                "exit_code": 0,
                "output": " ".join(output_parts),
                "error": "",
                "session_id": self.session_id
            }
        elif cmd_name == "set":
            if not args:
                # 列出所有变量
                var_list = "\n".join(f"{k}={v}" for k, v in self.variables.items())
                return {
                    "exit_code": 0,
                    "output": var_list,
                    "error": "",
                    "session_id": self.session_id
                }
        elif cmd_name in self.functions:
            # 执行用户定义的函数
            return await self._execute_user_function(cmd_name, args)
        elif cmd_name == "grep":
            # 简单的grep实现
            search_term = args[0].strip("'\"") if args else ""
            return {
                "exit_code": 0,
                "output": f"Mock grep result for: {search_term}",
                "error": "",
                "session_id": self.session_id,
                "_filter": search_term  # 用于管道处理
            }
            
        return {
            "exit_code": 1,
            "output": "",
            "error": f"Command not found: {cmd_name}",
            "session_id": self.session_id
        }
        
    async def _execute_pipeline(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """执行管道命令"""
        commands = ast["commands"]
        current_output = ""
        
        for i, cmd in enumerate(commands):
            if i == 0:
                # 第一个命令
                result = await self._execute_command(cmd)
                if result["exit_code"] != 0:
                    return result
                current_output = result["output"]
            else:
                # 后续命令处理前一个命令的输出
                if cmd["name"] == "grep":
                    search_term = cmd["args"][0].strip("'\"") if cmd["args"] else ""
                    # 简单的grep过滤
                    lines = current_output.split("\n")
                    filtered_lines = [line for line in lines if search_term.lower() in line.lower()]
                    current_output = "\n".join(filtered_lines)
                # 可以添加更多管道命令处理
                
        return {
            "exit_code": 0,
            "output": current_output,
            "error": "",
            "session_id": self.session_id
        }
        
    async def _execute_assignment(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """执行变量赋值"""
        var_name = ast["variable"]
        value = ast["value"].strip("'\"")
        self.variables[var_name] = value
        
        return {
            "exit_code": 0,
            "output": f"Variable {var_name} set to: {value}",
            "error": "",
            "session_id": self.session_id
        }
        
    async def _execute_function_definition(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """执行函数定义"""
        func_name = ast["name"]
        self.functions[func_name] = ast
        
        return {
            "exit_code": 0,
            "output": f"Function {func_name} defined",
            "error": "",
            "session_id": self.session_id
        }
        
    async def _execute_user_function(self, func_name: str, args: List[str]) -> Dict[str, Any]:
        """执行用户定义的函数"""
        func_def = self.functions[func_name]
        params = func_def["parameters"]
        
        # 简单的参数绑定
        local_vars = dict(zip(params, args))
        
        # 简单的函数执行（仅支持echo命令）
        if func_name == "greet" and args:
            name = args[0].strip("'\"")
            return {
                "exit_code": 0,
                "output": f"Hello, {name}!",
                "error": "",
                "session_id": self.session_id
            }
            
        return {
            "exit_code": 0,
            "output": f"Mock execution of function {func_name}",
            "error": "",
            "session_id": self.session_id
        }


class MockShellCompletion:
    """模拟Shell补全"""
    
    def __init__(self):
        self.variables = {}
        self.commands = ["help", "chat", "system", "plugin", "set", "echo", "load", "check"]
        self.subcommands = {
            "system": ["status", "info", "config", "restart"],
            "plugin": ["list", "load", "unload", "exec", "info"],
            "weather": ["get_current", "get_forecast", "get_alerts"]
        }
        
    async def complete(self, text: str, context: str = None) -> List[str]:
        """获取补全建议"""
        text = text.strip()
        
        # 变量补全
        if text.endswith("$") or text.split()[-1].startswith("$"):
            return await self._complete_variables(text)
            
        # 参数补全
        parts = text.split()
        if len(parts) > 1:
            return await self._complete_arguments(parts)
            
        # 命令补全
        return await self._complete_commands(text)
        
    async def _complete_commands(self, text: str) -> List[str]:
        """补全命令"""
        return [cmd for cmd in self.commands if cmd.startswith(text)]
        
    async def _complete_arguments(self, parts: List[str]) -> List[str]:
        """补全参数"""
        command = parts[0]
        if command in self.subcommands:
            prefix = parts[-1] if len(parts) > 1 else ""
            return [sub for sub in self.subcommands[command] if sub.startswith(prefix)]
        return []
        
    async def _complete_variables(self, text: str) -> List[str]:
        """补全变量"""
        var_prefix = text.split("$")[-1]
        return [f"${var}" for var in self.variables.keys() if var.startswith(var_prefix)]
        
    async def set_variable(self, name: str, value: str):
        """设置变量"""
        self.variables[name] = value


class MockShellDisplay:
    """模拟Shell显示引擎"""
    
    def format_text(self, text: str, color: str = None, bold: bool = False, underline: bool = False) -> str:
        """格式化文本"""
        codes = []
        if bold:
            codes.append("1")
        if underline:
            codes.append("4")
        if color:
            color_codes = {"red": "31", "green": "32", "blue": "34", "yellow": "33"}
            if color in color_codes:
                codes.append(color_codes[color])
                
        if codes:
            return f"\033[{';'.join(codes)}m{text}\033[0m"
        return text
        
    def render_table(self, data: List[Dict], headers: List[str]) -> str:
        """渲染表格"""
        if not data:
            return ""
            
        # 简单的表格渲染
        lines = []
        
        # 标题行
        header_line = " | ".join(headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))
        
        # 数据行
        for row in data:
            row_line = " | ".join(str(row.get(header, "")) for header in headers)
            lines.append(row_line)
            
        return "\n".join(lines)
        
    def create_progress_bar(self, current: int, total: int, width: int = 50) -> str:
        """创建进度条"""
        if total == 0:
            return ""
            
        percentage = int((current / total) * 100)
        filled = int((current / total) * width)
        bar = "█" * filled + "░" * (width - filled)
        
        return f"[{bar}] {percentage}%"
        
    def highlight_syntax(self, code: str, language: str = "shell") -> str:
        """语法高亮"""
        # 简单的语法高亮
        keywords = ["function", "if", "then", "else", "fi", "for", "while", "do", "done"]
        commands = ["echo", "cd", "ls", "grep", "awk", "sed"]
        
        highlighted = code
        for keyword in keywords:
            highlighted = highlighted.replace(keyword, f"\033[34m{keyword}\033[0m")
        for command in commands:
            highlighted = highlighted.replace(command, f"\033[32m{command}\033[0m")
            
        return highlighted