"""
函数式编程特性和内置函数库
"""

from typing import Any, List, Callable, Iterable, Optional, Union
from .objects import ListObject, ShellObjectError


class FunctionRegistry:
    """函数注册表"""
    
    def __init__(self):
        self.functions = {}
        self._register_builtin_functions()
    
    def register(self, name: str, func: Callable):
        """注册函数"""
        self.functions[name] = func
    
    def get(self, name: str) -> Optional[Callable]:
        """获取函数"""
        return self.functions.get(name)
    
    def call(self, name: str, args: List[Any]) -> Any:
        """调用函数"""
        func = self.get(name)
        if func is None:
            raise ShellObjectError(f"未知函数: {name}")
        
        try:
            return func(*args)
        except Exception as e:
            raise ShellObjectError(f"函数 {name} 执行失败: {e}")
    
    def _register_builtin_functions(self):
        """注册内置函数"""
        # 高阶函数
        self.register("map", self._builtin_map)
        self.register("filter", self._builtin_filter)
        self.register("reduce", self._builtin_reduce)
        self.register("forEach", self._builtin_forEach)
        
        # 集合函数
        self.register("range", self._builtin_range)
        self.register("len", self._builtin_len)
        self.register("sum", self._builtin_sum)
        self.register("min", self._builtin_min)
        self.register("max", self._builtin_max)
        self.register("sort", self._builtin_sort)
        self.register("reverse", self._builtin_reverse)
        self.register("unique", self._builtin_unique)
        
        # 字符串函数
        self.register("split", self._builtin_split)
        self.register("join", self._builtin_join)
        self.register("upper", self._builtin_upper)
        self.register("lower", self._builtin_lower)
        self.register("trim", self._builtin_trim)
        self.register("contains", self._builtin_contains)
        self.register("startsWith", self._builtin_startsWith)
        self.register("endsWith", self._builtin_endsWith)
        
        # 类型转换函数
        self.register("str", self._builtin_str)
        self.register("int", self._builtin_int)
        self.register("float", self._builtin_float)
        self.register("bool", self._builtin_bool)
        
        # 工具函数
        self.register("print", self._builtin_print)
        self.register("typeof", self._builtin_typeof)
        self.register("equals", self._builtin_equals)
    
    # 高阶函数实现
    def _builtin_map(self, func: Callable, iterable: Iterable) -> ListObject:
        """映射函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        elif isinstance(iterable, (list, tuple)):
            items = iterable
        else:
            items = list(iterable)
        
        result = [func(item) for item in items]
        return ListObject(result)
    
    def _builtin_filter(self, predicate: Callable, iterable: Iterable) -> ListObject:
        """过滤函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        elif isinstance(iterable, (list, tuple)):
            items = iterable
        else:
            items = list(iterable)
        
        result = [item for item in items if predicate(item)]
        return ListObject(result)
    
    def _builtin_reduce(self, func: Callable, iterable: Iterable, initial=None) -> Any:
        """归约函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        elif isinstance(iterable, (list, tuple)):
            items = iterable
        else:
            items = list(iterable)
        
        if not items and initial is None:
            raise ShellObjectError("reduce操作需要非空序列或初始值")
        
        if initial is not None:
            result = initial
            start_items = items
        else:
            result = items[0]
            start_items = items[1:]
        
        for item in start_items:
            result = func(result, item)
        
        return result
    
    def _builtin_forEach(self, func: Callable, iterable: Iterable) -> None:
        """遍历函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        elif isinstance(iterable, (list, tuple)):
            items = iterable
        else:
            items = list(iterable)
        
        for item in items:
            func(item)
    
    # 集合函数实现
    def _builtin_range(self, *args) -> ListObject:
        """范围函数"""
        if len(args) == 1:
            result = list(range(args[0]))
        elif len(args) == 2:
            result = list(range(args[0], args[1]))
        elif len(args) == 3:
            result = list(range(args[0], args[1], args[2]))
        else:
            raise ShellObjectError("range函数接受1-3个参数")
        
        return ListObject(result)
    
    def _builtin_len(self, obj: Any) -> int:
        """长度函数"""
        if hasattr(obj, 'items'):
            return len(obj.items)
        elif hasattr(obj, '__len__'):
            return len(obj)
        else:
            raise ShellObjectError(f"对象 {type(obj)} 没有长度")
    
    def _builtin_sum(self, iterable: Iterable) -> Union[int, float]:
        """求和函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        else:
            items = iterable
        
        return sum(items)
    
    def _builtin_min(self, iterable: Iterable) -> Any:
        """最小值函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        else:
            items = iterable
        
        return min(items)
    
    def _builtin_max(self, iterable: Iterable) -> Any:
        """最大值函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        else:
            items = iterable
        
        return max(items)
    
    def _builtin_sort(self, iterable: Iterable, key: Optional[Callable] = None, reverse: bool = False) -> ListObject:
        """排序函数"""
        if hasattr(iterable, 'items'):
            items = list(iterable.items)
        else:
            items = list(iterable)
        
        if key:
            result = sorted(items, key=key, reverse=reverse)
        else:
            result = sorted(items, reverse=reverse)
        
        return ListObject(result)
    
    def _builtin_reverse(self, iterable: Iterable) -> ListObject:
        """反转函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        else:
            items = list(iterable)
        
        return ListObject(list(reversed(items)))
    
    def _builtin_unique(self, iterable: Iterable) -> ListObject:
        """去重函数"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        else:
            items = list(iterable)
        
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        
        return ListObject(result)
    
    # 字符串函数实现
    def _builtin_split(self, text: str, separator: str = None) -> ListObject:
        """分割字符串"""
        if separator is None:
            result = text.split()
        else:
            result = text.split(separator)
        return ListObject(result)
    
    def _builtin_join(self, separator: str, iterable: Iterable) -> str:
        """连接字符串"""
        if hasattr(iterable, 'items'):
            items = iterable.items
        else:
            items = list(iterable)
        
        str_items = [str(item) for item in items]
        return separator.join(str_items)
    
    def _builtin_upper(self, text: str) -> str:
        """转大写"""
        return text.upper()
    
    def _builtin_lower(self, text: str) -> str:
        """转小写"""
        return text.lower()
    
    def _builtin_trim(self, text: str) -> str:
        """去除首尾空白"""
        return text.strip()
    
    def _builtin_contains(self, text: str, substring: str) -> bool:
        """包含检查"""
        return substring in text
    
    def _builtin_startsWith(self, text: str, prefix: str) -> bool:
        """前缀检查"""
        return text.startswith(prefix)
    
    def _builtin_endsWith(self, text: str, suffix: str) -> bool:
        """后缀检查"""
        return text.endswith(suffix)
    
    # 类型转换函数实现
    def _builtin_str(self, obj: Any) -> str:
        """转换为字符串"""
        return str(obj)
    
    def _builtin_int(self, obj: Any) -> int:
        """转换为整数"""
        return int(obj)
    
    def _builtin_float(self, obj: Any) -> float:
        """转换为浮点数"""
        return float(obj)
    
    def _builtin_bool(self, obj: Any) -> bool:
        """转换为布尔值"""
        return bool(obj)
    
    # 工具函数实现
    def _builtin_print(self, *args) -> None:
        """打印函数"""
        print(*args)
    
    def _builtin_typeof(self, obj: Any) -> str:
        """获取类型"""
        return type(obj).__name__
    
    def _builtin_equals(self, a: Any, b: Any) -> bool:
        """相等比较"""
        return a == b


class LambdaFunction:
    """Lambda函数包装器"""
    
    def __init__(self, params: List[str], body: Any, context: dict):
        self.params = params
        self.body = body
        self.context = context
    
    def __call__(self, *args):
        """执行Lambda函数"""
        if len(args) != len(self.params):
            raise ShellObjectError(f"Lambda函数期望 {len(self.params)} 个参数，但得到 {len(args)} 个")
        
        # 创建新的执行上下文
        local_context = self.context.copy()
        for param, arg in zip(self.params, args):
            local_context[param] = arg
        
        # 执行函数体（这里简化处理，实际需要AST解释器）
        # 暂时返回参数，实际应该执行self.body
        return args[0] if args else None


# 全局函数注册表
function_registry = FunctionRegistry()


# 便利函数
def register_function(name: str, func: Callable):
    """注册自定义函数"""
    function_registry.register(name, func)


def call_function(name: str, args: List[Any]) -> Any:
    """调用函数"""
    return function_registry.call(name, args)


def get_function(name: str) -> Optional[Callable]:
    """获取函数"""
    return function_registry.get(name)


# 常用高阶函数的便利别名
def map_func(func: Callable, iterable: Iterable) -> ListObject:
    """映射函数便利接口"""
    return function_registry._builtin_map(func, iterable)


def filter_func(predicate: Callable, iterable: Iterable) -> ListObject:
    """过滤函数便利接口"""
    return function_registry._builtin_filter(predicate, iterable)


def reduce_func(func: Callable, iterable: Iterable, initial=None) -> Any:
    """归约函数便利接口"""
    return function_registry._builtin_reduce(func, iterable, initial)