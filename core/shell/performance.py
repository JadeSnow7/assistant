"""
现代Shell性能优化和并行处理机制
"""

import asyncio
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import wraps, lru_cache
from typing import Any, List, Dict, Callable, Iterator, Optional, Union
import time
import psutil
from dataclasses import dataclass
from queue import Queue
import weakref

from .objects import ListObject, ShellObjectError


@dataclass
class PerformanceStats:
    """性能统计信息"""
    execution_time: float
    memory_usage: int
    cache_hits: int
    cache_misses: int
    parallel_tasks: int
    cpu_usage: float


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl  # 生存时间（秒）
        self.cache = {}
        self.access_times = {}
        self.creation_times = {}
        self.stats = {'hits': 0, 'misses': 0}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        current_time = time.time()
        
        # 检查是否存在且未过期
        if key in self.cache:
            if current_time - self.creation_times[key] < self.ttl:
                self.access_times[key] = current_time
                self.stats['hits'] += 1
                return self.cache[key]
            else:
                # 已过期，删除
                self._remove_key(key)
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        current_time = time.time()
        
        # 如果缓存已满，删除最久未使用的项
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()
        
        self.cache[key] = value
        self.access_times[key] = current_time
        self.creation_times[key] = current_time
    
    def _remove_key(self, key: str):
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            del self.creation_times[key]
    
    def _evict_lru(self):
        """删除最久未使用的项"""
        if not self.cache:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(lru_key)
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()
        self.creation_times.clear()
        self.stats = {'hits': 0, 'misses': 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': hit_rate,
            'memory_usage': self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> int:
        """估算内存使用量"""
        import sys
        total_size = 0
        
        try:
            for key, value in self.cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
        except:
            pass
        
        return total_size


class LazyEvaluator:
    """懒计算求值器"""
    
    def __init__(self, generator_func: Callable, *args, **kwargs):
        self.generator_func = generator_func
        self.args = args
        self.kwargs = kwargs
        self._cached_results = []
        self._exhausted = False
        self._generator = None
    
    def __iter__(self):
        # 先返回已缓存的结果
        for item in self._cached_results:
            yield item
        
        # 如果没有耗尽，继续生成
        if not self._exhausted:
            if self._generator is None:
                self._generator = self.generator_func(*self.args, **self.kwargs)
            
            try:
                while True:
                    item = next(self._generator)
                    self._cached_results.append(item)
                    yield item
            except StopIteration:
                self._exhausted = True
    
    def take(self, n: int) -> List[Any]:
        """取前n个元素"""
        result = []
        for i, item in enumerate(self):
            if i >= n:
                break
            result.append(item)
        return result
    
    def collect(self) -> List[Any]:
        """收集所有元素"""
        return list(self)


class ParallelExecutor:
    """并行执行器"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(32, (psutil.cpu_count() or 1) + 4)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=min(self.max_workers, psutil.cpu_count() or 1))
    
    async def parallel_map(self, func: Callable, items: List[Any], 
                          use_processes: bool = False) -> List[Any]:
        """并行映射操作"""
        if not items:
            return []
        
        # 小数据集不使用并行
        if len(items) < 10:
            return [func(item) for item in items]
        
        executor = self.process_pool if use_processes else self.thread_pool
        loop = asyncio.get_event_loop()
        
        try:
            futures = [loop.run_in_executor(executor, func, item) for item in items]
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            # 处理异常
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    raise result
                processed_results.append(result)
            
            return processed_results
        
        except Exception as e:
            raise ShellObjectError(f"并行映射失败: {e}")
    
    async def parallel_filter(self, predicate: Callable, items: List[Any],
                             use_processes: bool = False) -> List[Any]:
        """并行过滤操作"""
        if not items:
            return []
        
        if len(items) < 10:
            return [item for item in items if predicate(item)]
        
        executor = self.process_pool if use_processes else self.thread_pool
        loop = asyncio.get_event_loop()
        
        try:
            futures = [loop.run_in_executor(executor, predicate, item) for item in items]
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            filtered_items = []
            for item, result in zip(items, results):
                if isinstance(result, Exception):
                    raise result
                if result:
                    filtered_items.append(item)
            
            return filtered_items
        
        except Exception as e:
            raise ShellObjectError(f"并行过滤失败: {e}")
    
    def parallel_batch_process(self, func: Callable, items: List[Any], 
                              batch_size: int = None) -> Iterator[Any]:
        """批量并行处理"""
        if not items:
            return
        
        if batch_size is None:
            batch_size = max(1, len(items) // (self.max_workers * 2))
        
        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            futures = [self.thread_pool.submit(func, item) for item in batch]
            
            for future in as_completed(futures):
                try:
                    yield future.result()
                except Exception as e:
                    raise ShellObjectError(f"批量处理失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)


class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self):
        self.object_pool = {}
        self.weak_refs = weakref.WeakValueDictionary()
    
    def get_pooled_object(self, obj_type: str, *args, **kwargs):
        """获取池化对象"""
        key = (obj_type, str(args), str(sorted(kwargs.items())))
        
        if key in self.weak_refs:
            obj = self.weak_refs[key]
            if obj is not None:
                return obj
        
        # 创建新对象
        if obj_type == 'list':
            obj = ListObject(*args, **kwargs)
        else:
            raise ValueError(f"未知的对象类型: {obj_type}")
        
        self.weak_refs[key] = obj
        return obj
    
    def optimize_memory_usage(self):
        """优化内存使用"""
        import gc
        
        # 强制垃圾回收
        collected = gc.collect()
        
        # 清理弱引用
        dead_refs = [k for k, v in self.weak_refs.items() if v is None]
        for key in dead_refs:
            del self.weak_refs[key]
        
        return {
            'collected_objects': collected,
            'active_refs': len(self.weak_refs),
            'memory_usage': psutil.Process().memory_info().rss
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.parallel_executor = ParallelExecutor()
        self.memory_optimizer = MemoryOptimizer()
        self.metrics = {
            'total_executions': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'cache_stats': {},
            'memory_stats': {},
            'parallel_tasks': 0
        }
    
    def start_profiling(self, operation_name: str):
        """开始性能分析"""
        return PerformanceProfiler(operation_name, self)
    
    def record_execution(self, duration: float, cache_hit: bool = False):
        """记录执行性能"""
        self.metrics['total_executions'] += 1
        self.metrics['total_time'] += duration
        self.metrics['avg_time'] = self.metrics['total_time'] / self.metrics['total_executions']
        
        if cache_hit:
            self.cache_manager.stats['hits'] += 1
        else:
            self.cache_manager.stats['misses'] += 1
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'execution_metrics': self.metrics,
            'cache_stats': self.cache_manager.get_stats(),
            'memory_stats': self.memory_optimizer.optimize_memory_usage(),
            'system_resources': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent
            }
        }
    
    def optimize_performance(self):
        """执行性能优化"""
        optimizations = []
        
        # 内存优化
        memory_result = self.memory_optimizer.optimize_memory_usage()
        optimizations.append(f"内存清理: 回收了 {memory_result['collected_objects']} 个对象")
        
        # 缓存优化
        cache_stats = self.cache_manager.get_stats()
        if cache_stats['hit_rate'] < 0.5:
            optimizations.append("缓存命中率较低，建议增加缓存大小")
        
        # CPU优化建议
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > 80:
            optimizations.append("CPU使用率较高，建议使用并行处理")
        
        return optimizations
    
    def cleanup(self):
        """清理资源"""
        self.parallel_executor.cleanup()
        self.cache_manager.clear()


class PerformanceProfiler:
    """性能分析器上下文管理器"""
    
    def __init__(self, operation_name: str, monitor: PerformanceMonitor):
        self.operation_name = operation_name
        self.monitor = monitor
        self.start_time = None
        self.start_memory = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        duration = end_time - self.start_time
        memory_delta = end_memory - self.start_memory
        
        self.monitor.record_execution(duration)
        
        # 记录详细统计
        if not hasattr(self.monitor, 'operation_stats'):
            self.monitor.operation_stats = {}
        
        if self.operation_name not in self.monitor.operation_stats:
            self.monitor.operation_stats[self.operation_name] = {
                'count': 0,
                'total_time': 0.0,
                'total_memory': 0
            }
        
        stats = self.monitor.operation_stats[self.operation_name]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['total_memory'] += memory_delta


def performance_cache(ttl: int = 300):
    """性能缓存装饰器"""
    def decorator(func):
        cache = CacheManager(ttl=ttl)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 创建缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            
            return result
        
        wrapper.cache = cache
        return wrapper
    
    return decorator


def async_parallel(use_processes: bool = False):
    """异步并行装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(items: List[Any], *args, **kwargs):
            if not items:
                return []
            
            # 小数据集直接执行
            if len(items) < 10:
                return [func(item, *args, **kwargs) for item in items]
            
            # 并行执行
            executor = ParallelExecutor()
            try:
                if use_processes:
                    return await executor.parallel_map(
                        lambda item: func(item, *args, **kwargs), 
                        items, 
                        use_processes=True
                    )
                else:
                    return await executor.parallel_map(
                        lambda item: func(item, *args, **kwargs), 
                        items
                    )
            finally:
                executor.cleanup()
        
        return wrapper
    
    return decorator


class OptimizedListObject(ListObject):
    """优化的列表对象"""
    
    def __init__(self, items: List[Any]):
        super().__init__(items)
        self.performance_monitor = PerformanceMonitor()
    
    @performance_cache(ttl=60)
    def call_method(self, name: str, args: List[Any]) -> Any:
        """缓存优化的方法调用"""
        with self.performance_monitor.start_profiling(f"list_{name}"):
            return super().call_method(name, args)
    
    async def parallel_map(self, func: Callable) -> 'OptimizedListObject':
        """并行映射操作"""
        executor = ParallelExecutor()
        try:
            results = await executor.parallel_map(func, self.items)
            return OptimizedListObject(results)
        finally:
            executor.cleanup()
    
    async def parallel_filter(self, predicate: Callable) -> 'OptimizedListObject':
        """并行过滤操作"""
        executor = ParallelExecutor()
        try:
            results = await executor.parallel_filter(predicate, self.items)
            return OptimizedListObject(results)
        finally:
            executor.cleanup()
    
    def lazy_map(self, func: Callable) -> LazyEvaluator:
        """懒计算映射"""
        def generator():
            for item in self.items:
                yield func(item)
        
        return LazyEvaluator(generator)
    
    def lazy_filter(self, predicate: Callable) -> LazyEvaluator:
        """懒计算过滤"""
        def generator():
            for item in self.items:
                if predicate(item):
                    yield item
        
        return LazyEvaluator(generator)
    
    def batch_process(self, func: Callable, batch_size: int = None) -> Iterator[Any]:
        """批量处理"""
        executor = ParallelExecutor()
        try:
            yield from executor.parallel_batch_process(func, self.items, batch_size)
        finally:
            executor.cleanup()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_monitor.get_performance_report()


# 全局性能监控实例
global_performance_monitor = PerformanceMonitor()


def get_global_performance_stats() -> Dict[str, Any]:
    """获取全局性能统计"""
    return global_performance_monitor.get_performance_report()


def optimize_global_performance():
    """优化全局性能"""
    return global_performance_monitor.optimize_performance()


def cleanup_performance_resources():
    """清理性能监控资源"""
    global_performance_monitor.cleanup()