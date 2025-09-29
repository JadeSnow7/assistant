"""
现代Shell命令集成 - 将现代Shell语法集成到现有CLI系统
"""

import asyncio
from typing import List, Optional, Dict, Any
from ..command_router import CommandBase, CommandResult
from .parser import ModernShellParser, ParseError
from .executor import ModernShellExecutor, ExecutionError, Result
from .ai_assistant import AIShellAssistant
from .performance import global_performance_monitor, PerformanceProfiler


class ModernShellCommand(CommandBase):
    """现代Shell命令处理器"""
    
    def __init__(self):
        super().__init__(
            "msh", 
            "现代Shell语法解释器", 
            ["modernshell", "ms", "shell"]
        )
        self.parser = ModernShellParser()
        self.executor = ModernShellExecutor()
        self.ai_assistant = None  # 将在需要时初始化
        
        # 存储多行输入状态
        self.multiline_buffer = ""
        self.in_multiline = False
    
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行现代Shell命令"""
        if not args:
            return self._show_help()
        
        # 合并参数为完整命令
        command = " ".join(args)
        
        # 检查是否是特殊命令
        if command.strip() == "help":
            return self._show_help()
        elif command.strip() == "examples":
            return self._show_examples()
        elif command.strip() == "clear":
            self.multiline_buffer = ""
            self.in_multiline = False
            return CommandResult(True, content="多行缓冲区已清除")
        elif command.strip() == "stats":
            return self._show_performance_stats()
        elif command.strip().startswith("explain "):
            return await self._explain_command(command[8:].strip(), cli_controller)
        elif command.strip().startswith("complete "):
            return await self._get_completions(command[9:].strip(), cli_controller)
        
        try:
            # 处理多行输入
            if self._is_multiline_start(command):
                self.in_multiline = True
                self.multiline_buffer = command
                return CommandResult(
                    True, 
                    content="多行输入模式（输入'end'结束，'clear'清除）",
                    metadata={"multiline": True}
                )
            elif self.in_multiline:
                if command.strip() == "end":
                    # 执行多行命令
                    result = await self._execute_command(self.multiline_buffer, cli_controller)
                    self.multiline_buffer = ""
                    self.in_multiline = False
                    return result
                else:
                    # 继续累积多行输入
                    self.multiline_buffer += "\n" + command
                    return CommandResult(
                        True,
                        content=f"继续输入... ({len(self.multiline_buffer.split('\n'))} 行)",
                        metadata={"multiline": True}
                    )
            else:
                # 执行单行命令
                return await self._execute_command(command, cli_controller)
                
        except Exception as e:
            return CommandResult(
                False, 
                error=f"执行现代Shell命令时发生错误: {e}",
                metadata={"command": command}
            )
    
    def _is_multiline_start(self, command: str) -> bool:
        """检查是否是多行输入的开始"""
        # 简单的多行检测逻辑
        stripped = command.strip()
        return (
            stripped.endswith("{") or
            stripped.startswith("fn ") or
            stripped.startswith("class ") or
            stripped.startswith("if ") or
            stripped.startswith("for ") or
            stripped.startswith("while ")
        )
    
    async def _execute_command(self, command: str, cli_controller) -> CommandResult:
        """执行现代Shell命令"""
        with global_performance_monitor.start_profiling("modern_shell_execution"):
            try:
                # 解析命令
                ast = self.parser.parse(command)
                
                # 执行命令
                result = self.executor.execute(ast)
                
                if result.success:
                    # 格式化输出
                    output = self._format_result(result.value, result.type)
                    
                    return CommandResult(
                        True,
                        content=output,
                        metadata={
                            "syntax": "modern-shell",
                            "command": command,
                            "type": result.type.value if result.type else "unknown",
                            "performance_stats": global_performance_monitor.get_performance_report()
                        }
                    )
                else:
                    return CommandResult(
                        False,
                        error=result.error,
                        metadata={"command": command}
                    )
                    
            except ParseError as e:
                return CommandResult(
                    False,
                    error=f"语法错误: {e}",
                    metadata={"command": command, "line": getattr(e, 'line', 0)}
                )
            except ExecutionError as e:
                return CommandResult(
                    False,
                    error=f"执行错误: {e}",
                    metadata={"command": command, "line": getattr(e, 'line', 0)}
                )
    
    def _format_result(self, value: Any, result_type) -> str:
        """格式化结果输出"""
        if value is None:
            return "(无返回值)"
        
        # 根据类型格式化输出
        if hasattr(value, 'to_string'):
            return value.to_string()
        elif isinstance(value, (list, tuple)):
            if len(value) == 0:
                return "[]"
            elif len(value) == 1:
                return f"[{self._format_single_value(value[0])}]"
            else:
                items = [self._format_single_value(item) for item in value[:5]]
                if len(value) > 5:
                    items.append(f"... ({len(value) - 5} 更多)")
                return f"[{', '.join(items)}]"
        elif isinstance(value, dict):
            if len(value) == 0:
                return "{}"
            items = []
            for k, v in list(value.items())[:3]:
                items.append(f"{k}: {self._format_single_value(v)}")
            if len(value) > 3:
                items.append(f"... ({len(value) - 3} 更多)")
            return "{" + ", ".join(items) + "}"
        else:
            return str(value)
    
    def _format_single_value(self, value: Any) -> str:
        """格式化单个值"""
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        elif hasattr(value, 'to_string'):
            result = value.to_string()
            if len(result) > 50:
                return f"{result[:47]}..."
            return result
        else:
            result = str(value)
            if len(result) > 50:
                return f"{result[:47]}..."
            return result
    
    def _show_help(self) -> CommandResult:
        """显示帮助信息"""
        help_text = """现代Shell语法解释器

基本语法:
  let x = 42                    # 变量声明
  File("test.txt").read()       # 文件操作
  Files("*.py").map(f => f.size).sum()  # 函数式编程
  
对象系统:
  File(path)                    # 文件对象
  Dir(path)                     # 目录对象
  Process(cmd)                  # 进程对象
  System                        # 系统对象

函数式特性:
  map(func, list)              # 映射
  filter(predicate, list)      # 过滤
  reduce(func, list)           # 归约
  
管道操作:
  data | map(func) | filter(pred) | collect()

特殊命令:
  /msh help                    # 显示此帮助
  /msh examples               # 显示示例
  /msh stats                  # 显示性能统计
  /msh explain <命令>         # 解释命令含义
  /msh complete <部分命令>    # 获取补全建议
  /msh clear                  # 清除多行缓冲区
  
多行输入:
  - 以 {、fn、class、if 等开始自动进入多行模式
  - 输入 'end' 结束并执行
  - 输入 'clear' 清除缓冲区"""
        
        return CommandResult(True, content=help_text)
    
    def _show_examples(self) -> CommandResult:
        """显示使用示例"""
        examples_text = """现代Shell使用示例

文件操作:
  File("log.txt").lines().filter(line => contains(line, "ERROR")).count()
  Dir("/tmp").files.filter(f => f.size > 1000).map(f => f.name)
  
系统监控:
  System.cpu.usage
  System.memory.free
  Processes().filter(p => p.cpu > 80)
  
数据处理:
  range(1, 100) | filter(n => n % 2 == 0) | map(n => n * 2) | sum()
  Files("*.log") | map(f => f.lines().count()) | sum()
  
函数定义:
  fn double(x) { return x * 2 }
  let numbers = [1, 2, 3, 4, 5]
  numbers.map(double)
  
变量和计算:
  let pi = 3.14159
  let radius = 5
  let area = pi * radius * radius
  
条件语句:
  if (System.cpu.usage > 80) {
      print("CPU usage is high!")
  }"""
        
        return CommandResult(True, content=examples_text)
    
    def _show_performance_stats(self) -> CommandResult:
        """显示性能统计"""
        stats = global_performance_monitor.get_performance_report()
        
        stats_text = f"""现代Shell性能统计

📊 执行指标:
  总执行次数: {stats['execution_metrics']['total_executions']}
  平均执行时间: {stats['execution_metrics']['avg_time']:.3f}s
  总执行时间: {stats['execution_metrics']['total_time']:.3f}s

💾 缓存统计:
  缓存大小: {stats['cache_stats']['size']}/{stats['cache_stats']['max_size']}
  命中率: {stats['cache_stats']['hit_rate']:.2%}
  命中次数: {stats['cache_stats']['hits']}
  未命中: {stats['cache_stats']['misses']}

💻 系统资源:
  CPU使用率: {stats['system_resources']['cpu_percent']:.1f}%
  内存使用率: {stats['system_resources']['memory_percent']:.1f}%
  磁盘使用率: {stats['system_resources']['disk_usage']:.1f}%

🛠️ 内存优化:
  活跃引用: {stats['memory_stats']['active_refs']}
  内存使用: {stats['memory_stats']['memory_usage'] // 1024 // 1024}MB"""
        
        return CommandResult(True, content=stats_text)
    
    async def _explain_command(self, command: str, cli_controller) -> CommandResult:
        """解释命令含义"""
        try:
            # 初始化AI助手（如果需要）
            if self.ai_assistant is None:
                self.ai_assistant = AIShellAssistant(cli_controller.client)
            
            explanation = await self.ai_assistant.explain_command(command)
            
            if explanation:
                explanation_text = f"""命令解释: {command}

📝 语法分析:
  有效性: {'✅' if explanation['syntax_analysis']['valid'] else '❌'}
  AST类型: {explanation['syntax_analysis'].get('ast_type', 'N/A')}
  复杂度: {explanation['syntax_analysis'].get('complexity', 'N/A')}

🤖 AI解释:
  {explanation.get('ai_explanation', '未可用')}

📚 相关示例:
  {chr(10).join('- ' + ex for ex in explanation.get('examples', [])[:3])}

⚠️ 潜在问题:
  {chr(10).join('- ' + issue['message'] for issue in explanation.get('potential_issues', []))}"""
                
                return CommandResult(True, content=explanation_text)
            else:
                return CommandResult(False, error="无法解释该命令")
                
        except Exception as e:
            return CommandResult(False, error=f"解释命令失败: {e}")
    
    async def _get_completions(self, partial_command: str, cli_controller) -> CommandResult:
        """获取命令补全建议"""
        try:
            # 初始化AI助手（如果需要）
            if self.ai_assistant is None:
                self.ai_assistant = AIShellAssistant(cli_controller.client)
            
            completions = await self.ai_assistant.get_smart_completions(partial_command)
            
            if completions:
                completion_text = f"补全建议: {partial_command}\n\n"
                
                for i, completion in enumerate(completions[:10], 1):
                    completion_text += f"{i}. {completion['text']} - {completion['description']}\n"
                
                return CommandResult(True, content=completion_text)
            else:
                return CommandResult(True, content="暂无补全建议")
                
        except Exception as e:
            return CommandResult(False, error=f"获取补全建议失败: {e}")
    
    def get_help(self) -> str:
        """获取命令帮助"""
        return """现代Shell语法解释器
        
用法: /msh <command>
      /msh help        显示详细帮助
      /msh examples    显示使用示例
      
支持现代化的Shell语法，包括：
- 面向对象的文件/系统操作
- 函数式编程特性
- 管道数据处理
- 类型安全的变量系统
- Lambda表达式和高阶函数"""


class ModernShellIntegration:
    """现代Shell集成器"""
    
    def __init__(self, command_router):
        self.command_router = command_router
        self.modern_shell_cmd = ModernShellCommand()
    
    def integrate(self):
        """集成现代Shell到命令路由器"""
        self.command_router.register_command(self.modern_shell_cmd)
    
    def get_completion_suggestions(self, partial_command: str) -> List[str]:
        """获取命令补全建议"""
        suggestions = []
        
        # 对象构造函数
        if partial_command.startswith("F"):
            suggestions.extend(["File(", "Files("])
        elif partial_command.startswith("D"):
            suggestions.append("Dir(")
        elif partial_command.startswith("P"):
            suggestions.extend(["Process(", "Processes()"])
        elif partial_command.startswith("S"):
            suggestions.append("System")
        
        # 内置函数
        functions = ["map", "filter", "reduce", "range", "sum", "min", "max", "sort"]
        for func in functions:
            if func.startswith(partial_command.lower()):
                suggestions.append(f"{func}(")
        
        # 关键字
        keywords = ["let", "fn", "return", "if", "else", "for", "while", "try", "catch"]
        for keyword in keywords:
            if keyword.startswith(partial_command.lower()):
                suggestions.append(keyword)
        
        return suggestions
    
    def explain_command(self, command: str) -> str:
        """解释命令的含义"""
        try:
            parser = ModernShellParser()
            ast = parser.parse(command)
            
            # 简化的命令解释
            return self._explain_ast(ast)
        except:
            return "无法解析此命令"
    
    def _explain_ast(self, node) -> str:
        """解释AST节点"""
        if node.type == "function_call":
            func_name = node.children[0].value if node.children else "unknown"
            arg_count = len(node.children) - 1
            return f"调用函数 '{func_name}' 包含 {arg_count} 个参数"
        elif node.type == "pipeline":
            return "使用管道操作处理数据流"
        elif node.type == "let_statement":
            var_name = node.value.get("name", "unknown")
            return f"声明变量 '{var_name}'"
        elif node.type == "property_access":
            prop_name = node.value
            return f"访问属性 '{prop_name}'"
        else:
            return f"执行 {node.type} 操作"