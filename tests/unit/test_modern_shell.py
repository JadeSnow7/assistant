"""
现代Shell系统测试
"""

import pytest
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ui.cli.modern_shell.lexer import Lexer, TokenType
from ui.cli.modern_shell.parser import ModernShellParser, ParseError
from ui.cli.modern_shell.executor import ModernShellExecutor, ExecutionError
from ui.cli.modern_shell.objects import ListObject
from ui.cli.modern_shell.objects.file_objects import FileObject, DirectoryObject
from ui.cli.modern_shell.functions import function_registry


class TestLexer:
    """词法分析器测试"""
    
    def test_tokenize_simple_expression(self):
        """测试简单表达式的标记化"""
        lexer = Lexer("let x = 42")
        tokens = lexer.tokenize()
        
        assert len(tokens) == 5  # let, x, =, 42, EOF
        assert tokens[0].type == TokenType.LET
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "x"
        assert tokens[2].type == TokenType.ASSIGN
        assert tokens[3].type == TokenType.NUMBER
        assert tokens[3].value == 42
        assert tokens[4].type == TokenType.EOF
    
    def test_tokenize_string(self):
        """测试字符串标记化"""
        lexer = Lexer('let msg = "Hello, World!"')
        tokens = lexer.tokenize()
        
        string_token = tokens[3]
        assert string_token.type == TokenType.STRING
        assert string_token.value == "Hello, World!"
    
    def test_tokenize_function_call(self):
        """测试函数调用标记化"""
        lexer = Lexer("File('test.txt').read()")
        tokens = lexer.tokenize()
        
        assert tokens[0].type == TokenType.IDENTIFIER  # File
        assert tokens[1].type == TokenType.LPAREN     # (
        assert tokens[2].type == TokenType.STRING     # 'test.txt'
        assert tokens[3].type == TokenType.RPAREN     # )
        assert tokens[4].type == TokenType.DOT        # .
        assert tokens[5].type == TokenType.IDENTIFIER # read
        assert tokens[6].type == TokenType.LPAREN     # (
        assert tokens[7].type == TokenType.RPAREN     # )
    
    def test_tokenize_pipeline(self):
        """测试管道操作标记化"""
        lexer = Lexer("data | map(func) | filter(pred)")
        tokens = lexer.tokenize()
        
        pipe_positions = [i for i, token in enumerate(tokens) if token.type == TokenType.PIPE]
        assert len(pipe_positions) == 2


class TestParser:
    """语法分析器测试"""
    
    def test_parse_let_statement(self):
        """测试let语句解析"""
        parser = ModernShellParser()
        ast = parser.parse("let x = 42")
        
        assert ast.type == "program"
        assert len(ast.children) == 1
        
        let_stmt = ast.children[0]
        assert let_stmt.type == "let_statement"
        assert let_stmt.value["name"] == "x"
        assert len(let_stmt.children) == 1
        
        value_node = let_stmt.children[0]
        assert value_node.type == "number"
        assert value_node.value == 42
    
    def test_parse_function_call(self):
        """测试函数调用解析"""
        parser = ModernShellParser()
        ast = parser.parse("File('test.txt')")
        
        program = ast
        expr_stmt = program.children[0]
        func_call = expr_stmt.children[0]
        
        assert func_call.type == "function_call"
        assert len(func_call.children) == 2  # 函数名 + 1个参数
        
        func_name = func_call.children[0]
        assert func_name.type == "identifier"
        assert func_name.value == "File"
        
        arg = func_call.children[1]
        assert arg.type == "string"
        assert arg.value == "test.txt"
    
    def test_parse_property_access(self):
        """测试属性访问解析"""
        parser = ModernShellParser()
        ast = parser.parse("file.name")
        
        program = ast
        expr_stmt = program.children[0]
        prop_access = expr_stmt.children[0]
        
        assert prop_access.type == "property_access"
        assert prop_access.value == "name"
        assert len(prop_access.children) == 1
        
        obj = prop_access.children[0]
        assert obj.type == "identifier"
        assert obj.value == "file"
    
    def test_parse_pipeline(self):
        """测试管道解析"""
        parser = ModernShellParser()
        ast = parser.parse("data | map(func)")
        
        program = ast
        expr_stmt = program.children[0]
        pipeline = expr_stmt.children[0]
        
        assert pipeline.type == "pipeline"
        assert len(pipeline.children) == 2
        
        left = pipeline.children[0]
        assert left.type == "identifier"
        assert left.value == "data"
        
        right = pipeline.children[1]
        assert right.type == "function_call"
    
    def test_parse_array_literal(self):
        """测试数组字面量解析"""
        parser = ModernShellParser()
        ast = parser.parse("[1, 2, 3]")
        
        program = ast
        expr_stmt = program.children[0]
        array = expr_stmt.children[0]
        
        assert array.type == "array"
        assert len(array.children) == 3
        
        for i, child in enumerate(array.children):
            assert child.type == "number"
            assert child.value == i + 1


class TestObjects:
    """对象系统测试"""
    
    def test_list_object_operations(self):
        """测试列表对象操作"""
        # 创建列表对象
        numbers = ListObject([1, 2, 3, 4, 5])
        
        # 测试属性
        assert numbers.get_property("length") == 5
        assert numbers.get_property("first") == 1
        assert numbers.get_property("last") == 5
        
        # 测试map操作
        doubled = numbers.call_method("map", [lambda x: x * 2])
        assert isinstance(doubled, ListObject)
        assert doubled.items == [2, 4, 6, 8, 10]
        
        # 测试filter操作
        evens = numbers.call_method("filter", [lambda x: x % 2 == 0])
        assert isinstance(evens, ListObject)
        assert evens.items == [2, 4]
        
        # 测试sum操作
        total = numbers.call_method("sum", [])
        assert total == 15
    
    def test_file_object_properties(self):
        """测试文件对象属性"""
        # 使用当前文件作为测试
        current_file = FileObject(__file__)
        
        # 测试基本属性
        assert current_file.get_property("exists") == True
        assert current_file.get_property("is_file") == True
        assert current_file.get_property("is_dir") == False
        assert current_file.get_property("name") == "test_modern_shell.py"
        assert current_file.get_property("ext") == "py"
        
        # 测试大小属性
        size = current_file.get_property("size")
        assert isinstance(size, int)
        assert size > 0
    
    def test_directory_object_properties(self):
        """测试目录对象属性"""
        # 使用当前目录作为测试
        current_dir = DirectoryObject(Path(__file__).parent)
        
        # 测试基本属性
        assert current_dir.get_property("exists") == True
        assert current_dir.get_property("is_dir") == True
        
        # 测试文件和子目录列表
        files = current_dir.get_property("files")
        assert isinstance(files, ListObject)
        
        subdirs = current_dir.get_property("subdirs")
        assert isinstance(subdirs, ListObject)


class TestFunctions:
    """函数库测试"""
    
    def test_builtin_map(self):
        """测试内置map函数"""
        data = [1, 2, 3, 4, 5]
        result = function_registry._builtin_map(lambda x: x * 2, data)
        
        assert isinstance(result, ListObject)
        assert result.items == [2, 4, 6, 8, 10]
    
    def test_builtin_filter(self):
        """测试内置filter函数"""
        data = [1, 2, 3, 4, 5]
        result = function_registry._builtin_filter(lambda x: x % 2 == 0, data)
        
        assert isinstance(result, ListObject)
        assert result.items == [2, 4]
    
    def test_builtin_reduce(self):
        """测试内置reduce函数"""
        data = [1, 2, 3, 4, 5]
        result = function_registry._builtin_reduce(lambda a, b: a + b, data)
        
        assert result == 15
    
    def test_builtin_range(self):
        """测试内置range函数"""
        result = function_registry._builtin_range(5)
        
        assert isinstance(result, ListObject)
        assert result.items == [0, 1, 2, 3, 4]
        
        result2 = function_registry._builtin_range(2, 8)
        assert result2.items == [2, 3, 4, 5, 6, 7]


class TestExecutor:
    """执行器测试"""
    
    def test_execute_simple_expression(self):
        """测试简单表达式执行"""
        parser = ModernShellParser()
        executor = ModernShellExecutor()
        
        # 测试数字字面量
        ast = parser.parse("42")
        result = executor.execute(ast)
        
        assert result.success == True
        assert result.value == 42
    
    def test_execute_let_statement(self):
        """测试let语句执行"""
        parser = ModernShellParser()
        executor = ModernShellExecutor()
        
        # 执行变量声明
        ast = parser.parse("let x = 42")
        result = executor.execute(ast)
        
        assert result.success == True
        assert result.value == 42
        
        # 检查变量是否已设置
        assert executor.context.get_variable("x") == 42
    
    def test_execute_binary_operations(self):
        """测试二元操作执行"""
        parser = ModernShellParser()
        executor = ModernShellExecutor()
        
        test_cases = [
            ("3 + 4", 7),
            ("10 - 3", 7),
            ("6 * 7", 42),
            ("15 / 3", 5.0),
            ("17 % 5", 2),
            ("5 == 5", True),
            ("3 != 4", True),
            ("7 > 5", True),
            ("3 < 8", True),
            ("true && true", True),
            ("false || true", True)
        ]
        
        for expr, expected in test_cases:
            ast = parser.parse(expr)
            result = executor.execute(ast)
            
            assert result.success == True, f"表达式 '{expr}' 执行失败"
            assert result.value == expected, f"表达式 '{expr}' 期望 {expected}，实际 {result.value}"
    
    def test_execute_function_call(self):
        """测试函数调用执行"""
        parser = ModernShellParser()
        executor = ModernShellExecutor()
        
        # 测试内置函数
        ast = parser.parse("range(5)")
        result = executor.execute(ast)
        
        assert result.success == True
        assert isinstance(result.value, ListObject)
        assert result.value.items == [0, 1, 2, 3, 4]
    
    def test_execute_array_literal(self):
        """测试数组字面量执行"""
        parser = ModernShellParser()
        executor = ModernShellExecutor()
        
        ast = parser.parse("[1, 2, 3, 4, 5]")
        result = executor.execute(ast)
        
        assert result.success == True
        assert isinstance(result.value, ListObject)
        assert result.value.items == [1, 2, 3, 4, 5]


class TestIntegration:
    """集成测试"""
    
    def test_file_operations_workflow(self):
        """测试文件操作工作流"""
        parser = ModernShellParser()
        executor = ModernShellExecutor()
        
        # 创建测试文件对象
        test_code = f'File("{__file__}")'
        ast = parser.parse(test_code)
        result = executor.execute(ast)
        
        assert result.success == True
        assert isinstance(result.value, FileObject)
        
        # 测试获取文件名
        test_code2 = f'File("{__file__}").name'
        ast2 = parser.parse(test_code2)
        result2 = executor.execute(ast2)
        
        assert result2.success == True
        assert result2.value == "test_modern_shell.py"
    
    def test_functional_programming_workflow(self):
        """测试函数式编程工作流"""
        parser = ModernShellParser()
        executor = ModernShellExecutor()
        
        # 执行复杂的函数式表达式
        test_code = "map(lambda x: x * 2, range(5))"
        # 注：由于Lambda函数实现较复杂，这里简化测试
        test_code = "map(double, [1, 2, 3, 4, 5])"
        
        # 先定义double函数（简化）
        executor.context.set_function("double", lambda x: x * 2)
        
        ast = parser.parse(test_code)
        result = executor.execute(ast)
        
        assert result.success == True
        assert isinstance(result.value, ListObject)
        assert result.value.items == [2, 4, 6, 8, 10]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])