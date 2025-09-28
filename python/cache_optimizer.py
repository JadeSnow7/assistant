"""
缓存优化模块

提供多级缓存、智能缓存策略和缓存性能优化功能
"""

import time
import hashlib
import threading
import asyncio
import pickle
import json
import logging
from typing import Any, Dict, Optional, Callable, Union, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from collections import OrderedDict
from functools import wraps
import weakref


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl: Optional[float] = None
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at.timestamp() > self.ttl
    
    def touch(self):
        """更新访问时间"""
        self.accessed_at = datetime.now()
        self.access_count += 1


class CacheStrategy(ABC):
    """缓存策略抽象基类"""
    
    @abstractmethod
    def should_evict(self, cache: Dict[str, CacheEntry], max_size: int) -> List[str]:
        """确定应该驱逐的缓存键"""
        pass


class LRUStrategy(CacheStrategy):
    """最近最少使用策略"""
    
    def should_evict(self, cache: Dict[str, CacheEntry], max_size: int) -> List[str]:
        if len(cache) <= max_size:
            return []
        
        # 按访问时间排序，最旧的在前
        sorted_items = sorted(
            cache.items(),
            key=lambda x: x[1].accessed_at
        )
        
        evict_count = len(cache) - max_size
        return [key for key, _ in sorted_items[:evict_count]]


class LFUStrategy(CacheStrategy):
    """最少使用频率策略"""
    
    def should_evict(self, cache: Dict[str, CacheEntry], max_size: int) -> List[str]:
        if len(cache) <= max_size:
            return []
        
        # 按访问次数排序，最少的在前
        sorted_items = sorted(
            cache.items(),
            key=lambda x: (x[1].access_count, x[1].accessed_at)
        )
        
        evict_count = len(cache) - max_size
        return [key for key, _ in sorted_items[:evict_count]]


class TTLStrategy(CacheStrategy):
    """基于TTL的策略"""
    
    def should_evict(self, cache: Dict[str, CacheEntry], max_size: int) -> List[str]:
        # 首先移除过期的条目
        expired_keys = [key for key, entry in cache.items() if entry.is_expired]
        
        if len(cache) - len(expired_keys) <= max_size:
            return expired_keys
        
        # 如果仍然超过最大大小，使用LRU策略
        non_expired = {k: v for k, v in cache.items() if not v.is_expired}
        lru_strategy = LRUStrategy()
        additional_evictions = lru_strategy.should_evict(non_expired, max_size)
        
        return expired_keys + additional_evictions


class SmartCache:
    """智能缓存"""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        strategy: CacheStrategy = None,
        enable_stats: bool = True
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy or LRUStrategy()
        self.enable_stats = enable_stats
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _generate_key(self, key: Any) -> str:
        """生成缓存键"""
        if isinstance(key, str):
            return key
        
        # 对复杂对象生成哈希键
        if hasattr(key, '__dict__'):
            key_str = json.dumps(key.__dict__, sort_keys=True, default=str)
        else:
            key_str = str(key)
        
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: Any, default: Any = None) -> Any:
        """获取缓存值"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                
                if entry.is_expired:
                    del self._cache[cache_key]
                    self._update_stats('miss')
                    return default
                
                entry.touch()
                self._update_stats('hit')
                return entry.value
            
            self._update_stats('miss')
            return default
    
    def set(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值"""
        cache_key = self._generate_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        
        with self._lock:
            entry = CacheEntry(
                value=value,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                ttl=ttl
            )
            
            self._cache[cache_key] = entry
            self._update_stats('set')
            
            # 检查是否需要驱逐
            self._evict_if_needed()
    
    def delete(self, key: Any) -> bool:
        """删除缓存条目"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            if self.enable_stats:
                self._stats['size'] = 0
    
    def _evict_if_needed(self):
        """根据策略驱逐缓存"""
        if len(self._cache) <= self.max_size:
            return
        
        keys_to_evict = self.strategy.should_evict(self._cache, self.max_size)
        
        for key in keys_to_evict:
            if key in self._cache:
                del self._cache[key]
                self._update_stats('eviction')
    
    def _update_stats(self, operation: str):
        """更新统计信息"""
        if not self.enable_stats:
            return
        
        if operation in self._stats:
            self._stats[operation] += 1
        elif operation == 'eviction':
            self._stats['evictions'] += 1
        
        self._stats['size'] = len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'sets': self._stats['sets'],
                'evictions': self._stats['evictions'],
                'current_size': self._stats['size'],
                'max_size': self.max_size,
                'fill_ratio': self._stats['size'] / self.max_size
            }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况估算"""
        with self._lock:
            try:
                total_size = 0
                for entry in self._cache.values():
                    # 粗略估算对象大小
                    size = len(pickle.dumps(entry.value))
                    total_size += size
                
                avg_size = total_size / len(self._cache) if self._cache else 0
                
                return {
                    'total_bytes': total_size,
                    'average_entry_bytes': avg_size,
                    'entry_count': len(self._cache)
                }
            except Exception as e:
                logger.warning(f"Failed to calculate memory usage: {e}")
                return {'error': str(e)}


class MultiLevelCache:
    """多级缓存"""
    
    def __init__(self):
        self.levels: List[SmartCache] = []
        self._lock = threading.RLock()
    
    def add_level(self, cache: SmartCache) -> None:
        """添加缓存级别"""
        with self._lock:
            self.levels.append(cache)
    
    def get(self, key: Any, default: Any = None) -> Any:
        """从多级缓存获取值"""
        cache_key = key
        
        with self._lock:
            for i, cache in enumerate(self.levels):
                value = cache.get(cache_key)
                
                if value is not None:
                    # 将值写入更高级别的缓存
                    for j in range(i):
                        self.levels[j].set(cache_key, value)
                    
                    return value
            
            return default
    
    def set(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """设置多级缓存值"""
        with self._lock:
            # 写入所有级别
            for cache in self.levels:
                cache.set(key, value, ttl)
    
    def delete(self, key: Any) -> None:
        """从所有级别删除"""
        with self._lock:
            for cache in self.levels:
                cache.delete(key)
    
    def clear(self) -> None:
        """清空所有级别"""
        with self._lock:
            for cache in self.levels:
                cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有级别的统计"""
        with self._lock:
            return {
                f'level_{i}': cache.get_stats()
                for i, cache in enumerate(self.levels)
            }


# 全局缓存实例
default_cache = SmartCache(max_size=1000, default_ttl=3600)  # 1小时TTL


def cached(
    cache: Optional[SmartCache] = None,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None
):
    """
    缓存装饰器
    
    Args:
        cache: 使用的缓存实例
        ttl: 缓存过期时间
        key_func: 自定义键生成函数
    """
    def decorator(func):
        nonlocal cache
        if cache is None:
            cache = default_cache
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}.{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        # 添加缓存控制方法
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_stats = lambda: cache.get_stats()
        wrapper.cache_delete = lambda *args, **kwargs: cache.delete(
            key_func(*args, **kwargs) if key_func else 
            f"{func.__module__}.{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"
        )
        
        return wrapper
    
    return decorator


def async_cached(
    cache: Optional[SmartCache] = None,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None
):
    """异步缓存装饰器"""
    def decorator(func):
        nonlocal cache
        if cache is None:
            cache = default_cache
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                if asyncio.iscoroutinefunction(key_func):
                    cache_key = await key_func(*args, **kwargs)
                else:
                    cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}.{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行异步函数并缓存结果
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_stats = lambda: cache.get_stats()
        
        return wrapper
    
    return decorator


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.caches: Dict[str, SmartCache] = {}
        self._lock = threading.RLock()
    
    def create_cache(
        self,
        name: str,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        strategy: CacheStrategy = None
    ) -> SmartCache:
        """创建命名缓存"""
        with self._lock:
            cache = SmartCache(
                max_size=max_size,
                default_ttl=default_ttl,
                strategy=strategy
            )
            self.caches[name] = cache
            return cache
    
    def get_cache(self, name: str) -> Optional[SmartCache]:
        """获取命名缓存"""
        with self._lock:
            return self.caches.get(name)
    
    def delete_cache(self, name: str) -> bool:
        """删除命名缓存"""
        with self._lock:
            if name in self.caches:
                del self.caches[name]
                return True
            return False
    
    def clear_all(self) -> None:
        """清空所有缓存"""
        with self._lock:
            for cache in self.caches.values():
                cache.clear()
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存的统计"""
        with self._lock:
            return {
                name: cache.get_stats()
                for name, cache in self.caches.items()
            }
    
    def optimize_all(self) -> Dict[str, Any]:
        """优化所有缓存"""
        optimization_results = {}
        
        with self._lock:
            for name, cache in self.caches.items():
                stats = cache.get_stats()
                suggestions = []
                
                # 分析命中率
                if stats['hit_rate'] < 0.5:
                    suggestions.append("Consider increasing cache size or adjusting TTL")
                
                # 分析填充率
                if stats['fill_ratio'] > 0.9:
                    suggestions.append("Cache is nearly full, consider increasing max_size")
                
                # 分析驱逐率
                if stats['evictions'] > stats['sets'] * 0.1:
                    suggestions.append("High eviction rate, consider increasing cache size")
                
                optimization_results[name] = {
                    'stats': stats,
                    'suggestions': suggestions
                }
        
        return optimization_results


# 全局缓存管理器
cache_manager = CacheManager()


# 使用示例
@cached(ttl=300)  # 5分钟缓存
def expensive_computation(n: int) -> int:
    """示例耗时计算函数"""
    time.sleep(0.1)  # 模拟耗时操作
    return sum(range(n))


@async_cached(ttl=600)  # 10分钟缓存
async def async_expensive_operation(data: str) -> str:
    """示例异步耗时操作"""
    await asyncio.sleep(0.1)
    return data.upper()


if __name__ == "__main__":
    # 测试缓存功能
    print("Testing cache...")
    
    # 测试同步缓存
    result1 = expensive_computation(1000)
    result2 = expensive_computation(1000)  # 应该从缓存获取
    
    print(f"Cache stats: {expensive_computation.cache_stats()}")
    
    # 测试缓存管理器
    user_cache = cache_manager.create_cache("users", max_size=500, default_ttl=1800)
    user_cache.set("user_123", {"name": "John", "email": "john@example.com"})
    
    print(f"User cache stats: {user_cache.get_stats()}")
    print(f"All cache stats: {cache_manager.get_all_stats()}")
    print(f"Cache optimization: {cache_manager.optimize_all()}")