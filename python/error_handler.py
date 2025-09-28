"""
增强错误处理模块

提供统一的错误处理、重试机制、故障恢复和错误报告功能
"""

import logging
import time
import functools
import asyncio
import traceback
import threading
from typing import (
    Any, Callable, Dict, List, Optional, Union, Type, 
    Tuple, ClassVar, Protocol
)
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import json
import os


# 错误级别枚举
class ErrorLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# 重试策略枚举
class RetryStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    
    error_id: str
    error_type: str
    error_message: str
    function_name: str
    level: ErrorLevel
    timestamp: datetime
    stack_trace: str
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    retry_count: int = 0
    recovery_action: Optional[str] = None


@dataclass
class RetryConfig:
    """重试配置"""
    
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ignore_exceptions: Tuple[Type[Exception], ...] = ()


class ErrorHandler:
    """增强错误处理器"""
    
    def __init__(self):
        self.errors: deque = deque(maxlen=10000)
        self.error_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)
        self.recovery_actions: Dict[str, Callable] = {}
        self.lock = threading.RLock()
        self._error_counter = 0
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        
    def generate_error_id(self) -> str:
        """生成唯一错误ID"""
        with self.lock:
            self._error_counter += 1
            return f"ERR_{int(time.time())}_{self._error_counter:06d}"
    
    def record_error(
        self, 
        error: Exception, 
        function_name: str,
        level: ErrorLevel = ErrorLevel.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recovery_action: Optional[str] = None
    ) -> str:
        """记录错误"""
        error_id = self.generate_error_id()
        error_type = type(error).__name__
        
        error_info = ErrorInfo(
            error_id=error_id,
            error_type=error_type,
            error_message=str(error),
            function_name=function_name,
            level=level,
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc(),
            context=context or {},
            recovery_action=recovery_action
        )
        
        with self.lock:
            self.errors.append(error_info)
            self._update_error_stats(error_info)
            self._detect_error_patterns(error_info)
        
        # 记录日志
        log_level = self._get_log_level(level)
        self.logger.log(
            log_level,
            f"Error {error_id}: {error_type} in {function_name}: {str(error)}"
        )
        
        # 执行恢复操作
        if recovery_action and recovery_action in self.recovery_actions:
            try:
                self.recovery_actions[recovery_action]()
                self.logger.info(f"Recovery action '{recovery_action}' executed for error {error_id}")
            except Exception as recovery_error:
                self.logger.error(f"Recovery action failed: {recovery_error}")
        
        return error_id
    
    def _get_log_level(self, level: ErrorLevel) -> int:
        """获取日志级别"""
        mapping = {
            ErrorLevel.LOW: logging.INFO,
            ErrorLevel.MEDIUM: logging.WARNING,
            ErrorLevel.HIGH: logging.ERROR,
            ErrorLevel.CRITICAL: logging.CRITICAL
        }
        return mapping.get(level, logging.WARNING)
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """更新错误统计"""
        error_type = error_info.error_type
        stats = self.error_stats[error_type]
        
        if 'count' not in stats:
            stats.update({
                'count': 0,
                'first_seen': error_info.timestamp,
                'last_seen': error_info.timestamp,
                'functions': set(),
                'levels': defaultdict(int)
            })
        
        stats['count'] += 1
        stats['last_seen'] = error_info.timestamp
        stats['functions'].add(error_info.function_name)
        stats['levels'][error_info.level.value] += 1
    
    def _detect_error_patterns(self, error_info: ErrorInfo):
        """检测错误模式"""
        error_type = error_info.error_type
        recent_errors = [
            e for e in self.errors 
            if e.error_type == error_type and 
            e.timestamp > datetime.now() - timedelta(minutes=10)
        ]
        
        if len(recent_errors) >= 5:  # 10分钟内同类错误超过5次
            pattern = f"High frequency {error_type} errors"
            if pattern not in self.error_patterns[error_type]:
                self.error_patterns[error_type].append(pattern)
                self.logger.warning(f"Error pattern detected: {pattern}")
    
    def register_recovery_action(self, name: str, action: Callable):
        """注册恢复操作"""
        self.recovery_actions[name] = action
        self.logger.info(f"Recovery action '{name}' registered")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self.lock:
            total_errors = len(self.errors)
            critical_errors = len([e for e in self.errors if e.level == ErrorLevel.CRITICAL])
            
            # 转换统计数据为可序列化格式
            serializable_stats = {}
            for error_type, stats in self.error_stats.items():
                serializable_stats[error_type] = {
                    'count': stats['count'],
                    'first_seen': stats['first_seen'].isoformat(),
                    'last_seen': stats['last_seen'].isoformat(),
                    'functions': list(stats['functions']),
                    'levels': dict(stats['levels'])
                }
            
            return {
                'total_errors': total_errors,
                'critical_errors': critical_errors,
                'error_types': serializable_stats,
                'error_patterns': dict(self.error_patterns),
                'recent_errors': [
                    {
                        'error_id': e.error_id,
                        'error_type': e.error_type,
                        'function_name': e.function_name,
                        'level': e.level.value,
                        'timestamp': e.timestamp.isoformat()
                    }
                    for e in list(self.errors)[-10:]  # 最近10个错误
                ]
            }
    
    def get_error_by_id(self, error_id: str) -> Optional[ErrorInfo]:
        """根据ID获取错误信息"""
        with self.lock:
            for error in self.errors:
                if error.error_id == error_id:
                    return error
            return None
    
    def mark_error_resolved(self, error_id: str):
        """标记错误为已解决"""
        error = self.get_error_by_id(error_id)
        if error:
            error.resolved = True
            self.logger.info(f"Error {error_id} marked as resolved")
    
    def export_errors(self, file_path: str, include_stack_trace: bool = False):
        """导出错误信息"""
        with self.lock:
            errors_data = []
            for error in self.errors:
                error_dict = {
                    'error_id': error.error_id,
                    'error_type': error.error_type,
                    'error_message': error.error_message,
                    'function_name': error.function_name,
                    'level': error.level.value,
                    'timestamp': error.timestamp.isoformat(),
                    'context': error.context,
                    'resolved': error.resolved,
                    'retry_count': error.retry_count,
                    'recovery_action': error.recovery_action
                }
                
                if include_stack_trace:
                    error_dict['stack_trace'] = error.stack_trace
                
                errors_data.append(error_dict)
        
        with open(file_path, 'w') as f:
            json.dump({
                'export_time': datetime.now().isoformat(),
                'total_errors': len(errors_data),
                'errors': errors_data
            }, f, indent=2)
        
        self.logger.info(f"Errors exported to {file_path}")


# 全局错误处理器实例
error_handler = ErrorHandler()


def handle_errors(
    level: ErrorLevel = ErrorLevel.MEDIUM,
    recovery_action: Optional[str] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """
    错误处理装饰器
    
    Args:
        level: 错误级别
        recovery_action: 恢复操作名称
        reraise: 是否重新抛出异常
        default_return: 发生错误时的默认返回值
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_id = error_handler.record_error(
                    error=e,
                    function_name=f"{func.__module__}.{func.__name__}",
                    level=level,
                    context={'args': str(args), 'kwargs': str(kwargs)},
                    recovery_action=recovery_action
                )
                
                if reraise:
                    raise
                else:
                    return default_return
        
        return wrapper
    return decorator


def async_handle_errors(
    level: ErrorLevel = ErrorLevel.MEDIUM,
    recovery_action: Optional[str] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """异步错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_id = error_handler.record_error(
                    error=e,
                    function_name=f"{func.__module__}.{func.__name__}",
                    level=level,
                    context={'args': str(args), 'kwargs': str(kwargs)},
                    recovery_action=recovery_action
                )
                
                if reraise:
                    raise
                else:
                    return default_return
        
        return wrapper
    return decorator


def retry_on_failure(config: Optional[RetryConfig] = None):
    """
    失败重试装饰器
    
    Args:
        config: 重试配置
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.ignore_exceptions:
                    # 忽略的异常直接抛出
                    raise
                except config.exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # 最后一次尝试失败
                        error_handler.record_error(
                            error=e,
                            function_name=f"{func.__module__}.{func.__name__}",
                            level=ErrorLevel.HIGH,
                            context={
                                'attempt': attempt + 1,
                                'max_attempts': config.max_attempts,
                                'args': str(args),
                                'kwargs': str(kwargs)
                            }
                        )
                        raise
                    
                    # 计算延迟时间
                    delay = calculate_delay(attempt, config)
                    time.sleep(delay)
                    
                    # 记录重试
                    logging.warning(
                        f"Retrying {func.__name__} (attempt {attempt + 2}/{config.max_attempts}) "
                        f"after {delay:.2f}s delay. Error: {str(e)}"
                    )
            
            # 不应该到达这里
            raise last_exception
        
        return wrapper
    return decorator


def async_retry_on_failure(config: Optional[RetryConfig] = None):
    """异步失败重试装饰器"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.ignore_exceptions:
                    raise
                except config.exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        error_handler.record_error(
                            error=e,
                            function_name=f"{func.__module__}.{func.__name__}",
                            level=ErrorLevel.HIGH,
                            context={
                                'attempt': attempt + 1,
                                'max_attempts': config.max_attempts,
                                'args': str(args),
                                'kwargs': str(kwargs)
                            }
                        )
                        raise
                    
                    delay = calculate_delay(attempt, config)
                    await asyncio.sleep(delay)
                    
                    logging.warning(
                        f"Retrying {func.__name__} (attempt {attempt + 2}/{config.max_attempts}) "
                        f"after {delay:.2f}s delay. Error: {str(e)}"
                    )
            
            raise last_exception
        
        return wrapper
    return decorator


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """计算重试延迟时间"""
    if config.strategy == RetryStrategy.FIXED:
        return config.base_delay
    elif config.strategy == RetryStrategy.LINEAR:
        return min(config.base_delay * (attempt + 1), config.max_delay)
    elif config.strategy == RetryStrategy.EXPONENTIAL:
        return min(
            config.base_delay * (config.backoff_multiplier ** attempt),
            config.max_delay
        )
    else:
        return config.base_delay


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.RLock()
    
    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                if self.state == "OPEN":
                    if self._should_attempt_reset():
                        self.state = "HALF_OPEN"
                    else:
                        raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# 示例恢复操作
def restart_service():
    """重启服务恢复操作"""
    logging.info("Executing service restart recovery action")
    # 这里可以添加实际的重启逻辑


def clear_cache():
    """清理缓存恢复操作"""
    logging.info("Executing cache clear recovery action")
    # 这里可以添加实际的缓存清理逻辑


# 注册默认恢复操作
error_handler.register_recovery_action("restart_service", restart_service)
error_handler.register_recovery_action("clear_cache", clear_cache)


# 使用示例
@handle_errors(level=ErrorLevel.HIGH, recovery_action="clear_cache")
@retry_on_failure(RetryConfig(max_attempts=3, strategy=RetryStrategy.EXPONENTIAL))
def example_risky_function():
    """示例风险函数"""
    import random
    if random.random() < 0.7:  # 70% 概率失败
        raise ValueError("Random failure")
    return "Success"


@CircuitBreaker(failure_threshold=3, recovery_timeout=30)
def example_external_service():
    """示例外部服务调用"""
    import random
    if random.random() < 0.8:  # 80% 概率失败
        raise ConnectionError("External service unavailable")
    return "External service response"


if __name__ == "__main__":
    # 测试错误处理
    try:
        example_risky_function()
    except Exception:
        pass
    
    # 获取错误统计
    stats = error_handler.get_error_stats()
    print("Error Statistics:")
    print(json.dumps(stats, indent=2))