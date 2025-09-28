"""
性能监控和优化模块

提供应用性能监控、优化建议和性能指标收集功能
"""

import time
import functools
import logging
import threading
import psutil
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import json
import os
from datetime import datetime, timedelta

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    
    function_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    custom_metrics: Optional[Dict[str, Any]] = None


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.function_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.lock = threading.RLock()
        self._start_time = time.time()
        
    def record_metric(self, metric: PerformanceMetrics):
        """记录性能指标"""
        with self.lock:
            self.metrics.append(metric)
            self._update_function_stats(metric)
    
    def _update_function_stats(self, metric: PerformanceMetrics):
        """更新函数统计信息"""
        func_name = metric.function_name
        stats = self.function_stats[func_name]
        
        # 初始化统计信息
        if 'call_count' not in stats:
            stats.update({
                'call_count': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'error_count': 0,
                'total_memory': 0.0,
                'total_cpu': 0.0
            })
        
        # 更新统计信息
        stats['call_count'] += 1
        stats['total_time'] += metric.execution_time
        stats['min_time'] = min(stats['min_time'], metric.execution_time)
        stats['max_time'] = max(stats['max_time'], metric.execution_time)
        stats['total_memory'] += metric.memory_usage
        stats['total_cpu'] += metric.cpu_usage
        
        if not metric.success:
            stats['error_count'] += 1
        
        # 计算平均值
        stats['avg_time'] = stats['total_time'] / stats['call_count']
        stats['avg_memory'] = stats['total_memory'] / stats['call_count']
        stats['avg_cpu'] = stats['total_cpu'] / stats['call_count']
        stats['error_rate'] = stats['error_count'] / stats['call_count']
    
    def get_function_stats(self, function_name: Optional[str] = None) -> Dict[str, Any]:
        """获取函数统计信息"""
        with self.lock:
            if function_name:
                return self.function_stats.get(function_name, {})
            return dict(self.function_stats)
    
    def get_recent_metrics(self, count: int = 100) -> List[PerformanceMetrics]:
        """获取最近的性能指标"""
        with self.lock:
            return list(self.metrics)[-count:]
    
    def get_slow_functions(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """获取慢函数列表"""
        slow_functions = []
        
        with self.lock:
            for func_name, stats in self.function_stats.items():
                if stats.get('avg_time', 0) > threshold:
                    slow_functions.append({
                        'function_name': func_name,
                        'avg_time': stats['avg_time'],
                        'max_time': stats['max_time'],
                        'call_count': stats['call_count'],
                        'error_rate': stats['error_rate']
                    })
        
        return sorted(slow_functions, key=lambda x: x['avg_time'], reverse=True)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self.lock:
            total_calls = sum(stats.get('call_count', 0) for stats in self.function_stats.values())
            total_errors = sum(stats.get('error_count', 0) for stats in self.function_stats.values())
            
            return {
                'uptime_seconds': time.time() - self._start_time,
                'total_function_calls': total_calls,
                'total_errors': total_errors,
                'error_rate': total_errors / total_calls if total_calls > 0 else 0,
                'monitored_functions': len(self.function_stats),
                'metrics_collected': len(self.metrics)
            }


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()


def performance_trace(
    include_memory: bool = True,
    include_cpu: bool = True,
    custom_metrics: Optional[Callable] = None
):
    """
    性能追踪装饰器
    
    Args:
        include_memory: 是否包含内存使用监控
        include_cpu: 是否包含CPU使用监控
        custom_metrics: 自定义指标收集函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024 if include_memory else 0
            start_cpu = psutil.Process().cpu_percent() if include_cpu else 0
            
            success = True
            error_message = None
            result = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                logger.error(f"Error in {func.__name__}: {error_message}")
                raise
            finally:
                # 计算性能指标
                execution_time = time.time() - start_time
                memory_usage = (psutil.Process().memory_info().rss / 1024 / 1024 - start_memory) if include_memory else 0
                cpu_usage = psutil.Process().cpu_percent() - start_cpu if include_cpu else 0
                
                # 收集自定义指标
                custom_data = None
                if custom_metrics:
                    try:
                        custom_data = custom_metrics(result, args, kwargs)
                    except Exception as e:
                        logger.warning(f"Custom metrics collection failed: {e}")
                
                # 记录性能指标
                metric = PerformanceMetrics(
                    function_name=f"{func.__module__}.{func.__name__}",
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage,
                    timestamp=datetime.now(),
                    success=success,
                    error_message=error_message,
                    custom_metrics=custom_data
                )
                
                performance_monitor.record_metric(metric)
                
                # 记录慢函数警告
                if execution_time > 2.0:  # 超过2秒的函数
                    logger.warning(
                        f"Slow function detected: {func.__name__} took {execution_time:.2f}s"
                    )
        
        return wrapper
    return decorator


def async_performance_trace(
    include_memory: bool = True,
    include_cpu: bool = True,
    custom_metrics: Optional[Callable] = None
):
    """
    异步性能追踪装饰器
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024 if include_memory else 0
            start_cpu = psutil.Process().cpu_percent() if include_cpu else 0
            
            success = True
            error_message = None
            result = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                logger.error(f"Error in {func.__name__}: {error_message}")
                raise
            finally:
                # 计算性能指标
                execution_time = time.time() - start_time
                memory_usage = (psutil.Process().memory_info().rss / 1024 / 1024 - start_memory) if include_memory else 0
                cpu_usage = psutil.Process().cpu_percent() - start_cpu if include_cpu else 0
                
                # 收集自定义指标
                custom_data = None
                if custom_metrics:
                    try:
                        if asyncio.iscoroutinefunction(custom_metrics):
                            custom_data = await custom_metrics(result, args, kwargs)
                        else:
                            custom_data = custom_metrics(result, args, kwargs)
                    except Exception as e:
                        logger.warning(f"Custom metrics collection failed: {e}")
                
                # 记录性能指标
                metric = PerformanceMetrics(
                    function_name=f"{func.__module__}.{func.__name__}",
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage,
                    timestamp=datetime.now(),
                    success=success,
                    error_message=error_message,
                    custom_metrics=custom_data
                )
                
                performance_monitor.record_metric(metric)
                
                # 记录慢函数警告
                if execution_time > 2.0:
                    logger.warning(
                        f"Slow async function detected: {func.__name__} took {execution_time:.2f}s"
                    )
        
        return wrapper
    return decorator


@asynccontextmanager
async def performance_context(operation_name: str):
    """性能监控上下文管理器"""
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024
    start_cpu = psutil.Process().cpu_percent()
    
    success = True
    error_message = None
    
    try:
        yield
    except Exception as e:
        success = False
        error_message = str(e)
        raise
    finally:
        execution_time = time.time() - start_time
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
        cpu_usage = psutil.Process().cpu_percent() - start_cpu
        
        metric = PerformanceMetrics(
            function_name=operation_name,
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message
        )
        
        performance_monitor.record_metric(metric)


class PerformanceOptimizer:
    """性能优化器"""
    
    @staticmethod
    def analyze_performance() -> Dict[str, Any]:
        """分析性能并提供优化建议"""
        stats = performance_monitor.get_function_stats()
        slow_functions = performance_monitor.get_slow_functions(threshold=0.5)
        summary = performance_monitor.get_performance_summary()
        
        recommendations = []
        
        # 分析慢函数
        for func in slow_functions:
            if func['avg_time'] > 2.0:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'high',
                    'function': func['function_name'],
                    'issue': f"Function is slow (avg: {func['avg_time']:.2f}s)",
                    'suggestion': "Consider optimizing algorithm or adding caching"
                })
        
        # 分析错误率
        for func_name, func_stats in stats.items():
            error_rate = func_stats.get('error_rate', 0)
            if error_rate > 0.1:  # 错误率超过10%
                recommendations.append({
                    'type': 'reliability',
                    'priority': 'high',
                    'function': func_name,
                    'issue': f"High error rate ({error_rate:.1%})",
                    'suggestion': "Add better error handling and validation"
                })
        
        # 分析内存使用
        high_memory_functions = [
            (name, stats) for name, stats in stats.items()
            if stats.get('avg_memory', 0) > 50  # 平均使用超过50MB
        ]
        
        for func_name, func_stats in high_memory_functions:
            recommendations.append({
                'type': 'memory',
                'priority': 'medium',
                'function': func_name,
                'issue': f"High memory usage (avg: {func_stats['avg_memory']:.1f}MB)",
                'suggestion': "Optimize memory usage or implement memory pooling"
            })
        
        return {
            'summary': summary,
            'slow_functions': slow_functions,
            'recommendations': recommendations,
            'analysis_time': datetime.now().isoformat()
        }
    
    @staticmethod
    def export_metrics(file_path: str, format: str = 'json'):
        """导出性能指标"""
        data = {
            'summary': performance_monitor.get_performance_summary(),
            'function_stats': performance_monitor.get_function_stats(),
            'recent_metrics': [
                {
                    'function_name': m.function_name,
                    'execution_time': m.execution_time,
                    'memory_usage': m.memory_usage,
                    'cpu_usage': m.cpu_usage,
                    'timestamp': m.timestamp.isoformat(),
                    'success': m.success,
                    'error_message': m.error_message,
                    'custom_metrics': m.custom_metrics
                }
                for m in performance_monitor.get_recent_metrics(1000)
            ],
            'export_time': datetime.now().isoformat()
        }
        
        with open(file_path, 'w') as f:
            if format.lower() == 'json':
                json.dump(data, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Performance metrics exported to {file_path}")


class MemoryOptimizer:
    """内存优化器"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """获取内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent(),
            'available': psutil.virtual_memory().available / 1024 / 1024,  # MB
            'total': psutil.virtual_memory().total / 1024 / 1024  # MB
        }
    
    @staticmethod
    def suggest_optimizations() -> List[Dict[str, str]]:
        """提供内存优化建议"""
        memory_usage = MemoryOptimizer.get_memory_usage()
        suggestions = []
        
        if memory_usage['percent'] > 80:
            suggestions.append({
                'priority': 'high',
                'issue': f"High memory usage ({memory_usage['percent']:.1f}%)",
                'suggestion': "Consider implementing object pooling or reducing object lifecycle"
            })
        
        if memory_usage['rss'] > 1000:  # 超过1GB
            suggestions.append({
                'priority': 'medium',
                'issue': f"Large RSS memory ({memory_usage['rss']:.1f}MB)",
                'suggestion': "Review large data structures and implement lazy loading"
            })
        
        return suggestions


# 使用示例和测试函数
@performance_trace(include_memory=True, include_cpu=True)
def example_slow_function():
    """示例慢函数"""
    time.sleep(0.1)  # 模拟耗时操作
    return "completed"


@async_performance_trace()
async def example_async_function():
    """示例异步函数"""
    await asyncio.sleep(0.05)
    return "async completed"


if __name__ == "__main__":
    # 测试性能监控
    example_slow_function()
    
    # 分析性能
    analysis = PerformanceOptimizer.analyze_performance()
    print("Performance Analysis:")
    print(json.dumps(analysis, indent=2, default=str))
    
    # 内存使用情况
    memory_usage = MemoryOptimizer.get_memory_usage()
    print("\nMemory Usage:")
    print(json.dumps(memory_usage, indent=2))