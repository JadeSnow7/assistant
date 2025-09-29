"""
现代Shell执行器和类型系统
"""

import asyncio
from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass
from enum import Enum

from .lexer import ASTNode, ParseError
from .objects import ShellObject, ListObject, ShellObjectError
from .objects.file_objects import FileObject, DirectoryObject
from .objects.system_objects import ProcessObject, SystemObject, System
from .functions import function_registry, LambdaFunction
from .pipeline import Pipeline, StreamProcessor, TypeConverter


class ExecutionError(Exception):
    """执行错误"""
    
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(message)
        self.line = line
        self.column = column


class ShellType(Enum):
    """Shell类型枚举"""
    ANY = "Any"
    STRING = "String"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    FILE = "File"
    DIRECTORY = "Directory"
    PROCESS = "Process"
    SYSTEM = "System"
    LIST = "List"
    FUNCTION = "Function"
    PIPELINE = "Pipeline"
    STREAM = "Stream"


@dataclass
class Result:
    """执行结果包装器"""
    success: bool
    value: Any = None
    error: Optional[str] = None
    type: Optional[ShellType] = None
    
    @classmethod
    def ok(cls, value: Any, shell_type: Optional[ShellType] = None) -> 'Result':
        """成功结果"""
        return cls(True, value, None, shell_type)
    
    @classmethod
    def error(cls, message: str) -> 'Result':
        """错误结果"""
        return cls(False, None, message, None)


class ExecutionContext:
    """执行上下文"""
    
    def __init__(self, parent: Optional['ExecutionContext'] = None):
        self.parent = parent
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Any] = {}
        
        # 如果是根上下文，初始化内置对象
        if parent is None:
            self._init_builtins()
    
    def _init_builtins(self):
        """初始化内置对象和函数"""
        # 内置对象
        self.variables["System"] = System
        
        # 内置构造函数
        self.functions["File"] = FileObject
        self.functions["Dir"] = DirectoryObject
        self.functions["Process"] = ProcessObject
        
        # 内置函数
        for name, func in function_registry.functions.items():
            self.functions[name] = func
    
    def get_variable(self, name: str) -> Any:
        """获取变量"""
        if name in self.variables:
            return self.variables[name]
        elif self.parent:
            return self.parent.get_variable(name)
        else:
            raise ExecutionError(f"未定义的变量: {name}")
    
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value
    
    def get_function(self, name: str) -> Any:
        """获取函数"""
        if name in self.functions:
            return self.functions[name]
        elif self.parent:
            return self.parent.get_function(name)
        else:
            raise ExecutionError(f"未定义的函数: {name}")
    
    def set_function(self, name: str, func: Any):
        """设置函数"""
        self.functions[name] = func
    
    def create_child(self) -> 'ExecutionContext':
        """创建子上下文"""
        return ExecutionContext(self)


class TypeChecker:
    """类型检查器"""
    
    @staticmethod
    def get_type(value: Any) -> ShellType:
        """获取值的类型"""
        if isinstance(value, str):
            return ShellType.STRING
        elif isinstance(value, (int, float)):
            return ShellType.NUMBER
        elif isinstance(value, bool):
            return ShellType.BOOLEAN
        elif isinstance(value, FileObject):
            return ShellType.FILE
        elif isinstance(value, DirectoryObject):
            return ShellType.DIRECTORY
        elif isinstance(value, ProcessObject):
            return ShellType.PROCESS
        elif isinstance(value, SystemObject):
            return ShellType.SYSTEM
        elif isinstance(value, ListObject):
            return ShellType.LIST
        elif callable(value):
            return ShellType.FUNCTION
        elif isinstance(value, Pipeline):
            return ShellType.PIPELINE
        elif isinstance(value, StreamProcessor):
            return ShellType.STREAM
        else:
            return ShellType.ANY
    
    @staticmethod
    def is_compatible(value_type: ShellType, expected_type: ShellType) -> bool:
        """检查类型兼容性"""
        if expected_type == ShellType.ANY:
            return True
        return value_type == expected_type
    
    @staticmethod
    def cast(value: Any, target_type: ShellType) -> Any:
        """类型转换"""
        current_type = TypeChecker.get_type(value)
        
        if current_type == target_type:
            return value
        
        try:
            if target_type == ShellType.STRING:
                return str(value)
            elif target_type == ShellType.NUMBER:
                if isinstance(value, str):
                    return int(value) if value.isdigit() else float(value)
                return float(value)
            elif target_type == ShellType.BOOLEAN:
                return bool(value)
            elif target_type == ShellType.LIST:
                return TypeConverter.to_list(value)
            else:
                raise ExecutionError(f"无法将 {current_type.value} 转换为 {target_type.value}")
        except Exception as e:
            raise ExecutionError(f"类型转换失败: {e}")


class ModernShellExecutor:
    """现代Shell执行器"""
    
    def __init__(self):
        self.context = ExecutionContext()
        self.type_checker = TypeChecker()
    
    def execute(self, ast: ASTNode) -> Result:
        """执行AST"""
        try:
            result = self._eval_node(ast, self.context)
            return Result.ok(result, self.type_checker.get_type(result))
        except ExecutionError as e:
            return Result.error(str(e))
        except Exception as e:
            return Result.error(f"执行错误: {e}")
    
    def _eval_node(self, node: ASTNode, context: ExecutionContext) -> Any:
        """递归求值AST节点"""
        if node.type == "program":
            return self._eval_program(node, context)
        elif node.type == "let_statement":
            return self._eval_let_statement(node, context)
        elif node.type == "function_definition":
            return self._eval_function_definition(node, context)
        elif node.type == "expression_statement":
            return self._eval_expression_statement(node, context)
        elif node.type == "return_statement":
            return self._eval_return_statement(node, context)
        elif node.type == "if_statement":
            return self._eval_if_statement(node, context)
        elif node.type == "pipeline":
            return self._eval_pipeline(node, context)
        elif node.type == "binary_op":
            return self._eval_binary_op(node, context)
        elif node.type == "unary_op":
            return self._eval_unary_op(node, context)
        elif node.type == "function_call":
            return self._eval_function_call(node, context)
        elif node.type == "property_access":
            return self._eval_property_access(node, context)
        elif node.type == "index_access":
            return self._eval_index_access(node, context)
        elif node.type == "identifier":
            return self._eval_identifier(node, context)
        elif node.type == "string":
            return node.value
        elif node.type == "number":
            return node.value
        elif node.type == "boolean":
            return node.value
        elif node.type == "array":
            return self._eval_array(node, context)
        elif node.type == "object":
            return self._eval_object(node, context)
        else:
            raise ExecutionError(f"未知的AST节点类型: {node.type}")
    
    def _eval_program(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行程序"""
        result = None
        for child in node.children:
            result = self._eval_node(child, context)
        return result
    
    def _eval_let_statement(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行let语句"""
        name = node.value["name"]
        value_node = node.children[0]
        
        value = self._eval_node(value_node, context)
        context.set_variable(name, value)
        
        return value
    
    def _eval_function_definition(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行函数定义"""
        name = node.value["name"]
        parameters = node.value["parameters"]
        body = node.children
        
        # 创建函数对象
        def user_function(*args):
            if len(args) != len(parameters):
                raise ExecutionError(f"函数 {name} 期望 {len(parameters)} 个参数，但得到 {len(args)} 个")
            
            # 创建函数执行上下文
            func_context = context.create_child()
            
            # 绑定参数
            for param, arg in zip(parameters, args):
                func_context.set_variable(param["name"], arg)
            
            # 执行函数体
            result = None
            for stmt in body:
                result = self._eval_node(stmt, func_context)
                # 处理return语句（简化实现）
                if hasattr(result, '__return__'):
                    return result.__return__
            
            return result
        
        context.set_function(name, user_function)
        return user_function
    
    def _eval_expression_statement(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行表达式语句"""
        return self._eval_node(node.children[0], context)
    
    def _eval_return_statement(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行return语句"""
        if node.children:
            value = self._eval_node(node.children[0], context)
            # 使用特殊属性标记返回值（简化实现）
            value.__return__ = value
            return value
        return None
    
    def _eval_if_statement(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行if语句"""
        condition = self._eval_node(node.children[0], context)
        then_count = node.value["then_count"]
        else_count = node.value["else_count"]
        
        if condition:
            # 执行then分支
            result = None
            for i in range(1, then_count + 1):
                result = self._eval_node(node.children[i], context)
            return result
        elif else_count > 0:
            # 执行else分支
            result = None
            for i in range(then_count + 1, then_count + else_count + 1):
                result = self._eval_node(node.children[i], context)
            return result
        
        return None
    
    def _eval_pipeline(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行管道表达式"""
        left = self._eval_node(node.children[0], context)
        right_node = node.children[1]
        
        # 创建管道
        pipeline = Pipeline(left)
        
        # 如果右侧是函数调用，创建管道操作
        if right_node.type == "function_call":
            func_name_node = right_node.children[0]
            if func_name_node.type == "identifier":
                func_name = func_name_node.value
                args = [self._eval_node(arg, context) for arg in right_node.children[1:]]
                
                # 创建管道操作函数
                def pipe_operation(data):
                    # 将数据作为第一个参数传递给函数
                    func = context.get_function(func_name)
                    return func(data, *args)
                
                pipeline.add_stage(pipe_operation)
            else:
                raise ExecutionError("管道右侧必须是函数调用")
        else:
            # 直接执行右侧表达式（简化处理）
            right_result = self._eval_node(right_node, context)
            if callable(right_result):
                pipeline.add_stage(right_result)
            else:
                raise ExecutionError("管道右侧必须是可调用对象")
        
        return pipeline.execute()
    
    def _eval_binary_op(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行二元操作"""
        left = self._eval_node(node.children[0], context)
        right = self._eval_node(node.children[1], context)
        op = node.value
        
        if op == "+":
            return left + right
        elif op == "-":
            return left - right
        elif op == "*":
            return left * right
        elif op == "/":
            return left / right
        elif op == "%":
            return left % right
        elif op == "==":
            return left == right
        elif op == "!=":
            return left != right
        elif op == "<":
            return left < right
        elif op == ">":
            return left > right
        elif op == "<=":
            return left <= right
        elif op == ">=":
            return left >= right
        elif op == "&&":
            return left and right
        elif op == "||":
            return left or right
        else:
            raise ExecutionError(f"未知的二元操作符: {op}")
    
    def _eval_unary_op(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行一元操作"""
        operand = self._eval_node(node.children[0], context)
        op = node.value
        
        if op == "-":
            return -operand
        elif op == "!":
            return not operand
        else:
            raise ExecutionError(f"未知的一元操作符: {op}")
    
    def _eval_function_call(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行函数调用"""
        func_node = node.children[0]
        args = [self._eval_node(arg, context) for arg in node.children[1:]]
        
        if func_node.type == "identifier":
            func_name = func_node.value
            try:
                func = context.get_function(func_name)
                return func(*args)
            except Exception as e:
                raise ExecutionError(f"函数调用失败 {func_name}: {e}")
        else:
            # 复杂函数表达式
            func = self._eval_node(func_node, context)
            if callable(func):
                return func(*args)
            else:
                raise ExecutionError("尝试调用非函数对象")
    
    def _eval_property_access(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行属性访问"""
        obj = self._eval_node(node.children[0], context)
        prop_name = node.value
        
        if isinstance(obj, ShellObject):
            try:
                return obj.get_property(prop_name)
            except AttributeError as e:
                raise ExecutionError(str(e))
        elif hasattr(obj, prop_name):
            return getattr(obj, prop_name)
        else:
            raise ExecutionError(f"对象没有属性 '{prop_name}'")
    
    def _eval_index_access(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行索引访问"""
        obj = self._eval_node(node.children[0], context)
        index = self._eval_node(node.children[1], context)
        
        try:
            if isinstance(obj, ListObject):
                return obj.items[index]
            else:
                return obj[index]
        except (IndexError, KeyError, TypeError) as e:
            raise ExecutionError(f"索引访问失败: {e}")
    
    def _eval_identifier(self, node: ASTNode, context: ExecutionContext) -> Any:
        """执行标识符"""
        name = node.value
        try:
            return context.get_variable(name)
        except ExecutionError:
            # 尝试查找函数
            try:
                return context.get_function(name)
            except ExecutionError:
                raise ExecutionError(f"未定义的标识符: {name}")
    
    def _eval_array(self, node: ASTNode, context: ExecutionContext) -> ListObject:
        """执行数组字面量"""
        elements = [self._eval_node(child, context) for child in node.children]
        return ListObject(elements)
    
    def _eval_object(self, node: ASTNode, context: ExecutionContext) -> Dict[str, Any]:
        """执行对象字面量"""
        obj = {}
        for prop_node in node.children:
            key = prop_node.value
            value = self._eval_node(prop_node.children[0], context)
            obj[key] = value
        return obj