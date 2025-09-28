"""
AI智能补全和命令解释功能
"""

import asyncio
import re
from typing import List, Dict, Optional, Tuple, Any
from ui.shared.ai_client import EnhancedAIClient
from .parser import ModernShellParser, ParseError
from .executor import ModernShellExecutor
from .functions import function_registry


class AIShellAssistant:
    """AI Shell助手 - 提供智能补全和命令解释"""
    
    def __init__(self, ai_client: Optional[EnhancedAIClient] = None):
        self.ai_client = ai_client
        self.parser = ModernShellParser()
        self.executor = ModernShellExecutor()
        
        # 内置补全数据
        self.builtin_objects = ["File", "Dir", "Files", "Process", "Processes", "System"]
        self.builtin_functions = list(function_registry.functions.keys())
        self.builtin_keywords = ["let", "fn", "return", "if", "else", "for", "while", "try", "catch", "class", "extends"]
        self.builtin_operators = ["=>", "==", "!=", "<=", ">=", "&&", "||", "!", "+", "-", "*", "/", "%"]
        
        # 常用模式和示例
        self.common_patterns = {
            r"File\(": ['File("path/to/file.txt")', 'File(__file__)', 'File("data.json")'],
            r"Dir\(": ['Dir(".")', 'Dir("/home/user")', 'Dir("/tmp")'],
            r"Files\(": ['Files("*.py")', 'Files("*.txt", ".")', 'Files("**/*.log")'],
            r"\.map\(": ['map(x => x * 2)', 'map(f => f.size)', 'map(line => line.strip())'],
            r"\.filter\(": ['filter(x => x > 0)', 'filter(f => f.exists)', 'filter(line => line.contains("ERROR"))'],
            r"\.reduce\(": ['reduce((a, b) => a + b)', 'reduce((sum, x) => sum + x, 0)'],
            r"System\.": ['System.cpu.usage', 'System.memory.free', 'System.disk.usage("/")']
        }
    
    async def get_smart_completions(self, partial_command: str, cursor_position: int = None) -> List[Dict[str, Any]]:
        """获取智能补全建议"""
        if cursor_position is None:
            cursor_position = len(partial_command)
        
        completions = []
        
        # 1. 基础语法补全
        basic_completions = self._get_basic_completions(partial_command, cursor_position)
        completions.extend(basic_completions)
        
        # 2. 上下文相关补全
        context_completions = self._get_context_completions(partial_command, cursor_position)
        completions.extend(context_completions)
        
        # 3. AI增强补全（如果可用）
        if self.ai_client:
            ai_completions = await self._get_ai_completions(partial_command, cursor_position)
            completions.extend(ai_completions)
        
        # 去重并排序
        unique_completions = self._deduplicate_completions(completions)
        return sorted(unique_completions, key=lambda x: x.get('priority', 50))
    
    def _get_basic_completions(self, partial_command: str, cursor_position: int) -> List[Dict[str, Any]]:
        """获取基础语法补全"""
        completions = []
        
        # 提取当前光标位置的词
        before_cursor = partial_command[:cursor_position]
        current_word = re.search(r'\w*$', before_cursor)
        current_word = current_word.group() if current_word else ""
        
        # 关键字补全
        for keyword in self.builtin_keywords:
            if keyword.startswith(current_word.lower()):
                completions.append({
                    'text': keyword,
                    'type': 'keyword',
                    'description': f'关键字: {keyword}',
                    'priority': 10
                })
        
        # 内置对象补全
        for obj in self.builtin_objects:
            if obj.lower().startswith(current_word.lower()):
                completions.append({
                    'text': f'{obj}(',
                    'type': 'constructor',
                    'description': f'创建{obj}对象',
                    'priority': 20
                })
        
        # 内置函数补全
        for func in self.builtin_functions:
            if func.lower().startswith(current_word.lower()):
                completions.append({
                    'text': f'{func}(',
                    'type': 'function',
                    'description': f'内置函数: {func}',
                    'priority': 30
                })
        
        return completions
    
    def _get_context_completions(self, partial_command: str, cursor_position: int) -> List[Dict[str, Any]]:
        """获取上下文相关补全"""
        completions = []
        
        # 检查常用模式
        for pattern, suggestions in self.common_patterns.items():
            if re.search(pattern, partial_command):
                for suggestion in suggestions:
                    completions.append({
                        'text': suggestion,
                        'type': 'pattern',
                        'description': f'常用模式: {suggestion}',
                        'priority': 25
                    })
        
        # 链式调用补全
        if '.' in partial_command:
            chain_completions = self._get_chain_completions(partial_command, cursor_position)
            completions.extend(chain_completions)
        
        # 管道操作补全
        if '|' in partial_command:
            pipe_completions = self._get_pipe_completions(partial_command, cursor_position)
            completions.extend(pipe_completions)
        
        return completions
    
    def _get_chain_completions(self, partial_command: str, cursor_position: int) -> List[Dict[str, Any]]:
        """获取链式调用补全"""
        completions = []
        
        # 分析对象类型
        before_cursor = partial_command[:cursor_position]
        
        # 文件对象方法
        if re.search(r'File\([^)]*\)\.', before_cursor):
            file_methods = ['read()', 'write()', 'lines()', 'copy()', 'delete()', 'rename()']
            file_properties = ['name', 'size', 'exists', 'modified', 'parent']
            
            for method in file_methods:
                completions.append({
                    'text': method,
                    'type': 'method',
                    'description': f'文件方法: {method}',
                    'priority': 15
                })
            
            for prop in file_properties:
                completions.append({
                    'text': prop,
                    'type': 'property',
                    'description': f'文件属性: {prop}',
                    'priority': 15
                })
        
        # 目录对象方法
        elif re.search(r'Dir\([^)]*\)\.', before_cursor):
            dir_methods = ['find()', 'create()', 'delete()']
            dir_properties = ['files', 'subdirs', 'exists']
            
            for method in dir_methods:
                completions.append({
                    'text': method,
                    'type': 'method',
                    'description': f'目录方法: {method}',
                    'priority': 15
                })
            
            for prop in dir_properties:
                completions.append({
                    'text': prop,
                    'type': 'property',
                    'description': f'目录属性: {prop}',
                    'priority': 15
                })
        
        # 列表对象方法
        elif re.search(r'(\.files|\.subdirs|\[[^\]]*\])\.', before_cursor):
            list_methods = ['map()', 'filter()', 'reduce()', 'sort()', 'count()', 'sum()', 'join()']
            list_properties = ['length', 'first', 'last', 'empty']
            
            for method in list_methods:
                completions.append({
                    'text': method,
                    'type': 'method',
                    'description': f'列表方法: {method}',
                    'priority': 15
                })
            
            for prop in list_properties:
                completions.append({
                    'text': prop,
                    'type': 'property',
                    'description': f'列表属性: {prop}',
                    'priority': 15
                })
        
        # 系统对象属性
        elif 'System.' in before_cursor:
            system_properties = ['cpu.usage', 'memory.free', 'disk.usage', 'platform.system']
            
            for prop in system_properties:
                completions.append({
                    'text': prop,
                    'type': 'property',
                    'description': f'系统属性: {prop}',
                    'priority': 15
                })
        
        return completions
    
    def _get_pipe_completions(self, partial_command: str, cursor_position: int) -> List[Dict[str, Any]]:
        """获取管道操作补全"""
        completions = []
        
        # 管道后常用的操作
        pipe_operations = [
            'map(x => x)',
            'filter(x => x > 0)',
            'reduce((a, b) => a + b)',
            'sort()',
            'count()',
            'sum()',
            'join(", ")',
            'collect()'
        ]
        
        for op in pipe_operations:
            completions.append({
                'text': op,
                'type': 'pipe_operation',
                'description': f'管道操作: {op}',
                'priority': 20
            })
        
        return completions
    
    async def _get_ai_completions(self, partial_command: str, cursor_position: int) -> List[Dict[str, Any]]:
        """获取AI增强补全"""
        completions = []
        
        try:
            # 构建AI提示
            prompt = f"""
作为现代Shell语法专家，请为以下未完成的命令提供补全建议：

部分命令: {partial_command}
光标位置: {cursor_position}

请提供3-5个最可能的补全选项，每个选项包含：
1. 补全文本
2. 类型（keyword/function/method/property）
3. 简短描述

现代Shell支持：
- 对象操作：File(), Dir(), Process(), System
- 函数式编程：map(), filter(), reduce()
- 管道操作：data | operation
- 变量声明：let x = value

请以JSON格式返回，例如：
[
  {{"text": "map(", "type": "method", "description": "映射操作"}},
  {{"text": "filter(", "type": "method", "description": "过滤操作"}}
]
"""
            
            result = await self.ai_client.chat(prompt)
            
            if result and not result.get("error"):
                # 解析AI响应
                content = result.get("content", "")
                try:
                    import json
                    ai_suggestions = json.loads(content)
                    
                    for suggestion in ai_suggestions:
                        if isinstance(suggestion, dict):
                            completions.append({
                                'text': suggestion.get('text', ''),
                                'type': suggestion.get('type', 'ai_suggestion'),
                                'description': f"AI建议: {suggestion.get('description', '')}",
                                'priority': 5  # AI建议优先级最高
                            })
                except json.JSONDecodeError:
                    # AI响应格式不正确，忽略
                    pass
        
        except Exception:
            # AI调用失败，返回空列表
            pass
        
        return completions
    
    def _deduplicate_completions(self, completions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重补全建议"""
        seen = set()
        unique_completions = []
        
        for completion in completions:
            text = completion.get('text', '')
            if text and text not in seen:
                seen.add(text)
                unique_completions.append(completion)
        
        return unique_completions
    
    async def explain_command(self, command: str) -> Dict[str, Any]:
        """解释命令含义"""
        explanation = {
            'command': command,
            'syntax_analysis': None,
            'semantic_explanation': None,
            'ai_explanation': None,
            'examples': [],
            'potential_issues': []
        }
        
        # 1. 语法分析
        try:
            ast = self.parser.parse(command)
            explanation['syntax_analysis'] = self._analyze_syntax(ast)
        except ParseError as e:
            explanation['syntax_analysis'] = {
                'valid': False,
                'error': str(e),
                'error_position': getattr(e, 'line', 0)
            }
        
        # 2. 语义解释
        explanation['semantic_explanation'] = self._explain_semantics(command)
        
        # 3. AI增强解释
        if self.ai_client:
            explanation['ai_explanation'] = await self._get_ai_explanation(command)
        
        # 4. 相关示例
        explanation['examples'] = self._get_related_examples(command)
        
        # 5. 潜在问题检查
        explanation['potential_issues'] = self._check_potential_issues(command)
        
        return explanation
    
    def _analyze_syntax(self, ast) -> Dict[str, Any]:
        """分析语法结构"""
        return {
            'valid': True,
            'ast_type': ast.type,
            'components': self._extract_components(ast),
            'complexity': self._calculate_complexity(ast)
        }
    
    def _extract_components(self, node) -> List[Dict[str, str]]:
        """提取AST组件"""
        components = []
        
        if node.type == "function_call":
            func_name = node.children[0].value if node.children else "unknown"
            components.append({'type': 'function_call', 'name': func_name})
        elif node.type == "property_access":
            components.append({'type': 'property_access', 'name': node.value})
        elif node.type == "pipeline":
            components.append({'type': 'pipeline', 'name': '|'})
        elif node.type == "let_statement":
            var_name = node.value.get('name', 'unknown')
            components.append({'type': 'variable_declaration', 'name': var_name})
        
        # 递归处理子节点
        for child in node.children:
            components.extend(self._extract_components(child))
        
        return components
    
    def _calculate_complexity(self, node) -> str:
        """计算表达式复杂度"""
        def count_nodes(n):
            count = 1
            for child in n.children:
                count += count_nodes(child)
            return count
        
        total_nodes = count_nodes(node)
        
        if total_nodes <= 3:
            return "简单"
        elif total_nodes <= 8:
            return "中等"
        else:
            return "复杂"
    
    def _explain_semantics(self, command: str) -> Dict[str, Any]:
        """语义解释"""
        semantic_info = {
            'primary_action': None,
            'data_flow': [],
            'objects_used': [],
            'operations': []
        }
        
        # 识别主要动作
        if 'let ' in command:
            semantic_info['primary_action'] = '变量声明'
        elif '.map(' in command:
            semantic_info['primary_action'] = '数据映射'
        elif '.filter(' in command:
            semantic_info['primary_action'] = '数据过滤'
        elif '|' in command:
            semantic_info['primary_action'] = '管道处理'
        elif 'File(' in command:
            semantic_info['primary_action'] = '文件操作'
        elif 'Dir(' in command:
            semantic_info['primary_action'] = '目录操作'
        
        # 提取使用的对象类型
        for obj_type in self.builtin_objects:
            if obj_type in command:
                semantic_info['objects_used'].append(obj_type)
        
        # 提取操作序列
        operations = []
        if '.map(' in command:
            operations.append('映射变换')
        if '.filter(' in command:
            operations.append('条件过滤')
        if '.reduce(' in command:
            operations.append('聚合计算')
        if '.sort(' in command:
            operations.append('排序')
        if '.count(' in command:
            operations.append('计数')
        
        semantic_info['operations'] = operations
        
        return semantic_info
    
    async def _get_ai_explanation(self, command: str) -> Optional[str]:
        """获取AI解释"""
        try:
            prompt = f"""
请解释这个现代Shell命令的作用和工作原理：

命令: {command}

请用中文解释：
1. 这个命令的主要目的是什么
2. 它是如何工作的（数据流程）
3. 可能的使用场景
4. 需要注意的地方

请用简洁清晰的语言回答。
"""
            
            result = await self.ai_client.chat(prompt)
            
            if result and not result.get("error"):
                return result.get("content", "")
        
        except Exception:
            pass
        
        return None
    
    def _get_related_examples(self, command: str) -> List[str]:
        """获取相关示例"""
        examples = []
        
        # 基于命令内容提供相关示例
        if 'File(' in command:
            examples.extend([
                'File("data.txt").read()',
                'File("log.txt").lines().count()',
                'File("config.json").exists'
            ])
        
        if 'Dir(' in command:
            examples.extend([
                'Dir(".").files.count()',
                'Dir("/tmp").find("*.log")',
                'Dir("src").files.filter(f => f.ext == "py")'
            ])
        
        if '.map(' in command:
            examples.extend([
                '[1,2,3].map(x => x * 2)',
                'Files("*.py").map(f => f.size)',
                'words.map(w => w.upper())'
            ])
        
        if '.filter(' in command:
            examples.extend([
                '[1,2,3,4,5].filter(x => x > 3)',
                'Files("*").filter(f => f.size > 1000)',
                'lines.filter(line => line.contains("ERROR"))'
            ])
        
        # 去重并限制数量
        unique_examples = list(set(examples))
        return unique_examples[:5]
    
    def _check_potential_issues(self, command: str) -> List[Dict[str, str]]:
        """检查潜在问题"""
        issues = []
        
        # 检查常见问题
        if 'File(' in command and not ('exists' in command or 'try' in command):
            issues.append({
                'type': 'warning',
                'message': '建议在文件操作前检查文件是否存在',
                'suggestion': '使用 file.exists 或 try-catch 结构'
            })
        
        if '.map(' in command and '.filter(' in command:
            if command.index('.filter(') > command.index('.map('):
                issues.append({
                    'type': 'optimization',
                    'message': '建议先filter后map以提高性能',
                    'suggestion': '过滤可以减少需要处理的数据量'
                })
        
        if '/' in command and 'windows' in str(self.executor.context.get_variable('System')).lower():
            issues.append({
                'type': 'compatibility',
                'message': 'Windows系统路径分隔符建议使用反斜杠',
                'suggestion': '使用 Path() 对象处理跨平台路径'
            })
        
        return issues
    
    def get_command_suggestions(self, intent: str) -> List[Dict[str, Any]]:
        """根据意图获取命令建议"""
        suggestions = []
        
        intent_patterns = {
            '文件操作': [
                {'command': 'File("path").read()', 'description': '读取文件内容'},
                {'command': 'File("path").lines().count()', 'description': '统计文件行数'},
                {'command': 'Files("*.ext").map(f => f.size).sum()', 'description': '计算文件总大小'}
            ],
            '目录管理': [
                {'command': 'Dir("path").files.count()', 'description': '统计目录文件数'},
                {'command': 'Dir("path").find("*.py")', 'description': '查找特定类型文件'},
                {'command': 'Dir("path").files.filter(f => f.size > 1MB)', 'description': '查找大文件'}
            ],
            '数据处理': [
                {'command': 'data.map(x => transform(x))', 'description': '数据变换'},
                {'command': 'data.filter(x => condition(x))', 'description': '数据过滤'},
                {'command': 'data | process1() | process2()', 'description': '管道处理'}
            ],
            '系统监控': [
                {'command': 'System.cpu.usage', 'description': '查看CPU使用率'},
                {'command': 'System.memory.free', 'description': '查看可用内存'},
                {'command': 'Processes().filter(p => p.cpu > 80)', 'description': '查找高CPU进程'}
            ]
        }
        
        # 模糊匹配意图
        for pattern, commands in intent_patterns.items():
            if any(keyword in intent.lower() for keyword in pattern.split()):
                suggestions.extend(commands)
        
        return suggestions[:10]  # 限制返回数量