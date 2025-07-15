"""
Performance Optimizer for RecRadiko Keyboard Navigation UI

Provides performance optimization utilities for keyboard navigation screens
including memory management, response time optimization, and resource pooling.

Key optimizations:
- Memory pooling for UI components
- Lazy loading of heavy resources
- Caching frequently accessed data
- Optimized rendering for large lists
- Background prefetching for common operations
"""

import gc
import time
import threading
import weakref
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from functools import lru_cache, wraps
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future
import psutil
import os
from pathlib import Path

# Type definitions
T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    operation_name: str
    start_time: float
    end_time: float
    memory_before: int
    memory_after: int
    cpu_percent: float
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def memory_delta(self) -> int:
        return self.memory_after - self.memory_before


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process()
        self._lock = threading.Lock()
    
    def start_operation(self, operation_name: str) -> dict:
        """Start monitoring an operation"""
        return {
            'operation_name': operation_name,
            'start_time': time.time(),
            'memory_before': self.process.memory_info().rss,
            'cpu_percent': self.process.cpu_percent()
        }
    
    def end_operation(self, operation_context: dict) -> PerformanceMetrics:
        """End monitoring an operation and record metrics"""
        metrics = PerformanceMetrics(
            operation_name=operation_context['operation_name'],
            start_time=operation_context['start_time'],
            end_time=time.time(),
            memory_before=operation_context['memory_before'],
            memory_after=self.process.memory_info().rss,
            cpu_percent=operation_context['cpu_percent']
        )
        
        with self._lock:
            self.metrics.append(metrics)
        
        return metrics
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        with self._lock:
            if not self.metrics:
                return {}
            
            durations = [m.duration for m in self.metrics]
            memory_deltas = [m.memory_delta for m in self.metrics]
            
            return {
                'total_operations': len(self.metrics),
                'average_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'min_duration': min(durations),
                'average_memory_delta': sum(memory_deltas) / len(memory_deltas),
                'max_memory_delta': max(memory_deltas),
                'operations_by_name': self._group_by_operation()
            }
    
    def _group_by_operation(self) -> Dict[str, Dict[str, float]]:
        """Group metrics by operation name"""
        grouped = {}
        for metric in self.metrics:
            if metric.operation_name not in grouped:
                grouped[metric.operation_name] = []
            grouped[metric.operation_name].append(metric.duration)
        
        result = {}
        for op_name, durations in grouped.items():
            result[op_name] = {
                'count': len(durations),
                'average': sum(durations) / len(durations),
                'max': max(durations),
                'min': min(durations)
            }
        
        return result


class MemoryPool(Generic[T]):
    """Generic memory pool for object reuse"""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self.pool: List[T] = []
        self._lock = threading.Lock()
    
    def acquire(self) -> T:
        """Acquire an object from the pool"""
        with self._lock:
            if self.pool:
                return self.pool.pop()
            else:
                return self.factory()
    
    def release(self, obj: T) -> None:
        """Release an object back to the pool"""
        with self._lock:
            if len(self.pool) < self.max_size:
                # Reset object state if it has a reset method
                if hasattr(obj, 'reset'):
                    obj.reset()
                self.pool.append(obj)
    
    def clear(self) -> None:
        """Clear the entire pool"""
        with self._lock:
            self.pool.clear()
    
    def size(self) -> int:
        """Get current pool size"""
        with self._lock:
            return len(self.pool)


class ResourceCache:
    """Cache for frequently accessed resources"""
    
    def __init__(self, max_size: int = 100, ttl: float = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry['timestamp'] < self.ttl:
                    entry['access_count'] += 1
                    return entry['value']
                else:
                    del self.cache[key]
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache"""
        with self._lock:
            # Clean up expired entries
            self._cleanup_expired()
            
            # Remove oldest entry if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), 
                               key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]
            
            self.cache[key] = {
                'value': value,
                'timestamp': time.time(),
                'access_count': 1
            }
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def clear(self) -> None:
        """Clear entire cache"""
        with self._lock:
            self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_accesses = sum(entry['access_count'] for entry in self.cache.values())
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'total_accesses': total_accesses,
                'hit_ratio': total_accesses / max(1, len(self.cache))
            }


class BackgroundTaskManager:
    """Manager for background task execution"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks: Dict[str, Future] = {}
        self._lock = threading.Lock()
    
    def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> Future:
        """Submit a background task"""
        with self._lock:
            # Cancel existing task with same ID
            if task_id in self.active_tasks:
                self.active_tasks[task_id].cancel()
            
            future = self.executor.submit(func, *args, **kwargs)
            self.active_tasks[task_id] = future
            
            # Clean up completed tasks
            self._cleanup_completed_tasks()
            
            return future
    
    def get_task_result(self, task_id: str, timeout: float = 0.1) -> Optional[Any]:
        """Get result of a background task"""
        with self._lock:
            if task_id in self.active_tasks:
                future = self.active_tasks[task_id]
                try:
                    return future.result(timeout=timeout)
                except Exception:
                    return None
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a background task"""
        with self._lock:
            if task_id in self.active_tasks:
                success = self.active_tasks[task_id].cancel()
                if success:
                    del self.active_tasks[task_id]
                return success
            return False
    
    def _cleanup_completed_tasks(self) -> None:
        """Remove completed tasks from active tasks"""
        completed_tasks = [
            task_id for task_id, future in self.active_tasks.items()
            if future.done()
        ]
        for task_id in completed_tasks:
            del self.active_tasks[task_id]
    
    def shutdown(self) -> None:
        """Shutdown the task manager"""
        with self._lock:
            for future in self.active_tasks.values():
                future.cancel()
            self.active_tasks.clear()
        self.executor.shutdown(wait=True)


class LazyLoader:
    """Lazy loading utility for expensive resources"""
    
    def __init__(self, loader_func: Callable[[], T], cache_result: bool = True):
        self.loader_func = loader_func
        self.cache_result = cache_result
        self._cached_result: Optional[T] = None
        self._loaded = False
        self._lock = threading.Lock()
    
    def load(self) -> T:
        """Load the resource"""
        if self._loaded and self.cache_result:
            return self._cached_result
        
        with self._lock:
            if self._loaded and self.cache_result:
                return self._cached_result
            
            result = self.loader_func()
            
            if self.cache_result:
                self._cached_result = result
                self._loaded = True
            
            return result
    
    def reset(self) -> None:
        """Reset the lazy loader"""
        with self._lock:
            self._cached_result = None
            self._loaded = False


class PerformanceOptimizer:
    """Main performance optimizer class"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.resource_cache = ResourceCache()
        self.background_tasks = BackgroundTaskManager()
        self.memory_pools: Dict[str, MemoryPool] = {}
        self.lazy_loaders: Dict[str, LazyLoader] = {}
        self._gc_threshold = 100  # Operations before forced GC
        self._operation_count = 0
    
    def create_memory_pool(self, name: str, factory: Callable[[], T], max_size: int = 10) -> MemoryPool[T]:
        """Create a memory pool for object reuse"""
        pool = MemoryPool(factory, max_size)
        self.memory_pools[name] = pool
        return pool
    
    def create_lazy_loader(self, name: str, loader_func: Callable[[], T], cache_result: bool = True) -> LazyLoader:
        """Create a lazy loader for expensive resources"""
        loader = LazyLoader(loader_func, cache_result)
        self.lazy_loaders[name] = loader
        return loader
    
    def optimize_memory(self) -> None:
        """Perform memory optimization"""
        # Clear unused pools
        for pool in self.memory_pools.values():
            if pool.size() > pool.max_size // 2:
                pool.clear()
        
        # Clear cache if it's getting large
        if len(self.resource_cache.cache) > self.resource_cache.max_size * 0.8:
            self.resource_cache.clear()
        
        # Force garbage collection
        gc.collect()
    
    def prefetch_resource(self, key: str, loader_func: Callable[[], Any]) -> None:
        """Prefetch a resource in the background"""
        def prefetch_task():
            if self.resource_cache.get(key) is None:
                result = loader_func()
                self.resource_cache.set(key, result)
        
        self.background_tasks.submit_task(f"prefetch_{key}", prefetch_task)
    
    def monitor_operation(self, operation_name: str):
        """Decorator for monitoring operation performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                context = self.monitor.start_operation(operation_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.monitor.end_operation(context)
                    self._operation_count += 1
                    
                    # Periodic memory optimization
                    if self._operation_count % self._gc_threshold == 0:
                        self.optimize_memory()
            
            return wrapper
        return decorator
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'performance_metrics': self.monitor.get_metrics_summary(),
            'cache_stats': self.resource_cache.stats(),
            'memory_pools': {
                name: pool.size() for name, pool in self.memory_pools.items()
            },
            'active_background_tasks': len(self.background_tasks.active_tasks),
            'system_memory': {
                'rss': psutil.Process().memory_info().rss,
                'vms': psutil.Process().memory_info().vms,
                'cpu_percent': psutil.Process().cpu_percent()
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown the performance optimizer"""
        self.background_tasks.shutdown()
        for pool in self.memory_pools.values():
            pool.clear()
        self.resource_cache.clear()


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


def optimize_performance(operation_name: str):
    """Decorator for automatic performance optimization"""
    return performance_optimizer.monitor_operation(operation_name)


def cache_result(key: str, ttl: float = 300):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache first
            cached_result = performance_optimizer.resource_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Compute and cache result
            result = func(*args, **kwargs)
            performance_optimizer.resource_cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


def prefetch_data(key: str, loader_func: Callable[[], Any]):
    """Utility function for prefetching data"""
    performance_optimizer.prefetch_resource(key, loader_func)


def get_memory_pool(name: str) -> Optional[MemoryPool]:
    """Get a memory pool by name"""
    return performance_optimizer.memory_pools.get(name)


def get_lazy_loader(name: str) -> Optional[LazyLoader]:
    """Get a lazy loader by name"""
    return performance_optimizer.lazy_loaders.get(name)


def optimize_memory():
    """Trigger memory optimization"""
    performance_optimizer.optimize_memory()


def get_performance_report() -> Dict[str, Any]:
    """Get performance report"""
    return performance_optimizer.get_performance_report()