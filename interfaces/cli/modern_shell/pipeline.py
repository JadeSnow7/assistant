"""
管道处理系统 - 支持数据流处理和类型转换
"""

import asyncio
from typing import Any, List, Callable, Iterable, Optional, Union, Generator
from .objects import ListObject, ShellObjectError


class PipelineError(Exception):
    """管道处理错误"""
    pass


class Pipeline:
    """管道处理器"""
    
    def __init__(self, initial_data: Any = None):
        self.stages = []
        self.initial_data = initial_data
    
    def add_stage(self, operation: Callable[[Any], Any]):
        """添加管道阶段"""
        self.stages.append(operation)
        return self
    
    def pipe(self, operation: Callable[[Any], Any]):
        """管道操作（流畅接口）"""
        return self.add_stage(operation)
    
    def execute(self, input_data: Any = None) -> Any:
        """执行管道"""
        data = input_data if input_data is not None else self.initial_data
        
        if data is None:
            raise PipelineError("没有输入数据")
        
        try:
            result = data
            for stage in self.stages:
                result = stage(result)
            return result
        except Exception as e:
            raise PipelineError(f"管道执行失败: {e}")
    
    def __or__(self, other):
        """重载 | 操作符"""
        if callable(other):
            return self.pipe(other)
        else:
            raise PipelineError("管道右侧必须是可调用对象")


class StreamProcessor:
    """流处理器 - 支持懒计算"""
    
    def __init__(self, data_source: Iterable):
        if hasattr(data_source, 'items'):
            self.data_source = iter(data_source.items)
        elif isinstance(data_source, Iterable):
            self.data_source = iter(data_source)
        else:
            self.data_source = iter([data_source])
        
        self.operations = []
    
    def map(self, func: Callable) -> 'StreamProcessor':
        """映射操作"""
        self.operations.append(('map', func))
        return self
    
    def filter(self, predicate: Callable) -> 'StreamProcessor':
        """过滤操作"""
        self.operations.append(('filter', predicate))
        return self
    
    def take(self, count: int) -> 'StreamProcessor':
        """取前N个元素"""
        self.operations.append(('take', count))
        return self
    
    def skip(self, count: int) -> 'StreamProcessor':
        """跳过前N个元素"""
        self.operations.append(('skip', count))
        return self
    
    def distinct(self) -> 'StreamProcessor':
        """去重操作"""
        self.operations.append(('distinct', None))
        return self
    
    def sort(self, key: Optional[Callable] = None, reverse: bool = False) -> 'StreamProcessor':
        """排序操作"""
        self.operations.append(('sort', (key, reverse)))
        return self
    
    def collect(self) -> ListObject:
        """收集结果为列表"""
        return ListObject(list(self._generate()))
    
    def to_list(self) -> List[Any]:
        """转换为Python列表"""
        return list(self._generate())
    
    def count(self) -> int:
        """计算元素数量"""
        return sum(1 for _ in self._generate())
    
    def sum(self) -> Union[int, float]:
        """求和"""
        return sum(self._generate())
    
    def min(self) -> Any:
        """最小值"""
        return min(self._generate())
    
    def max(self) -> Any:
        """最大值"""
        return max(self._generate())
    
    def first(self) -> Optional[Any]:
        """第一个元素"""
        try:
            return next(self._generate())
        except StopIteration:
            return None
    
    def any(self, predicate: Optional[Callable] = None) -> bool:
        """是否存在满足条件的元素"""
        if predicate:
            return any(predicate(x) for x in self._generate())
        else:
            return any(self._generate())
    
    def all(self, predicate: Optional[Callable] = None) -> bool:
        """是否所有元素都满足条件"""
        if predicate:
            return all(predicate(x) for x in self._generate())
        else:
            return all(self._generate())
    
    def foreach(self, action: Callable) -> 'StreamProcessor':
        """对每个元素执行操作"""
        for item in self._generate():
            action(item)
        return self
    
    def _generate(self) -> Generator[Any, None, None]:
        """生成器 - 执行所有流操作"""
        current_stream = self.data_source
        
        for op_type, op_arg in self.operations:
            if op_type == 'map':
                current_stream = (op_arg(item) for item in current_stream)
            
            elif op_type == 'filter':
                current_stream = (item for item in current_stream if op_arg(item))
            
            elif op_type == 'take':
                current_stream = self._take(current_stream, op_arg)
            
            elif op_type == 'skip':
                current_stream = self._skip(current_stream, op_arg)
            
            elif op_type == 'distinct':
                current_stream = self._distinct(current_stream)
            
            elif op_type == 'sort':
                # 排序需要完全实现，不能保持懒计算
                key_func, reverse = op_arg
                items = list(current_stream)
                if key_func:
                    items.sort(key=key_func, reverse=reverse)
                else:
                    items.sort(reverse=reverse)
                current_stream = iter(items)
        
        # 返回最终流
        yield from current_stream
    
    def _take(self, stream: Iterable, count: int) -> Generator[Any, None, None]:
        """取前N个元素的生成器"""
        for i, item in enumerate(stream):
            if i >= count:
                break
            yield item
    
    def _skip(self, stream: Iterable, count: int) -> Generator[Any, None, None]:
        """跳过前N个元素的生成器"""
        for i, item in enumerate(stream):
            if i >= count:
                yield item
    
    def _distinct(self, stream: Iterable) -> Generator[Any, None, None]:
        """去重生成器"""
        seen = set()
        for item in stream:
            if item not in seen:
                seen.add(item)
                yield item


class ParallelStreamProcessor:
    """并行流处理器"""
    
    def __init__(self, data_source: Iterable, max_workers: int = 4):
        self.data_source = data_source
        self.max_workers = max_workers
        self.operations = []
    
    def map(self, func: Callable) -> 'ParallelStreamProcessor':
        """并行映射操作"""
        self.operations.append(('map', func))
        return self
    
    def filter(self, predicate: Callable) -> 'ParallelStreamProcessor':
        """并行过滤操作"""
        self.operations.append(('filter', predicate))
        return self
    
    async def collect(self) -> ListObject:
        """异步收集结果"""
        import concurrent.futures
        
        if hasattr(self.data_source, 'items'):
            items = self.data_source.items
        else:
            items = list(self.data_source)
        
        # 执行并行操作
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            result = items
            
            for op_type, op_func in self.operations:
                if op_type == 'map':
                    # 并行映射
                    futures = [executor.submit(op_func, item) for item in result]
                    result = [future.result() for future in concurrent.futures.as_completed(futures)]
                
                elif op_type == 'filter':
                    # 并行过滤
                    futures = [executor.submit(op_func, item) for item in result]
                    filtered_items = []
                    for item, future in zip(result, futures):
                        if future.result():
                            filtered_items.append(item)
                    result = filtered_items
        
        return ListObject(result)


class TypeConverter:
    """类型转换器"""
    
    @staticmethod
    def to_list(obj: Any) -> ListObject:
        """转换为列表对象"""
        if isinstance(obj, ListObject):
            return obj
        elif hasattr(obj, 'items'):
            return ListObject(obj.items)
        elif isinstance(obj, (list, tuple)):
            return ListObject(list(obj))
        elif isinstance(obj, str):
            return ListObject(list(obj))
        elif hasattr(obj, '__iter__'):
            return ListObject(list(obj))
        else:
            return ListObject([obj])
    
    @staticmethod
    def to_stream(obj: Any) -> StreamProcessor:
        """转换为流处理器"""
        return StreamProcessor(obj)
    
    @staticmethod
    def to_string(obj: Any) -> str:
        """转换为字符串"""
        if hasattr(obj, 'to_string'):
            return obj.to_string()
        else:
            return str(obj)
    
    @staticmethod
    def to_number(obj: Any) -> Union[int, float]:
        """转换为数字"""
        if isinstance(obj, (int, float)):
            return obj
        elif isinstance(obj, str):
            try:
                # 尝试整数转换
                if '.' not in obj:
                    return int(obj)
                else:
                    return float(obj)
            except ValueError:
                raise PipelineError(f"无法将 '{obj}' 转换为数字")
        else:
            raise PipelineError(f"无法将 {type(obj)} 转换为数字")


# 便利函数
def pipe(data: Any) -> Pipeline:
    """创建管道"""
    return Pipeline(data)


def stream(data: Any) -> StreamProcessor:
    """创建流处理器"""
    return StreamProcessor(data)


def parallel_stream(data: Any, max_workers: int = 4) -> ParallelStreamProcessor:
    """创建并行流处理器"""
    return ParallelStreamProcessor(data, max_workers)


# 管道操作函数
def map_pipe(func: Callable) -> Callable[[Any], Any]:
    """管道映射操作"""
    def pipe_func(data):
        return TypeConverter.to_list(data).call_method("map", [func])
    return pipe_func


def filter_pipe(predicate: Callable) -> Callable[[Any], Any]:
    """管道过滤操作"""
    def pipe_func(data):
        return TypeConverter.to_list(data).call_method("filter", [predicate])
    return pipe_func


def sort_pipe(key: Optional[Callable] = None, reverse: bool = False) -> Callable[[Any], Any]:
    """管道排序操作"""
    def pipe_func(data):
        return TypeConverter.to_list(data).call_method("sort", [key, reverse])
    return pipe_func


def take_pipe(count: int) -> Callable[[Any], Any]:
    """管道取前N个操作"""
    def pipe_func(data):
        return TypeConverter.to_stream(data).take(count).collect()
    return pipe_func


def skip_pipe(count: int) -> Callable[[Any], Any]:
    """管道跳过前N个操作"""  
    def pipe_func(data):
        return TypeConverter.to_stream(data).skip(count).collect()
    return pipe_func