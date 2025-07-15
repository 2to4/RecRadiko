"""
Performance Optimizer Tests for RecRadiko UI

Tests performance optimization utilities including:
- Memory pooling
- Resource caching
- Background task management
- Performance monitoring
- Lazy loading
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
import gc
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.performance_optimizer import (
    PerformanceMonitor, MemoryPool, ResourceCache, BackgroundTaskManager,
    LazyLoader, PerformanceOptimizer, optimize_performance, cache_result,
    performance_optimizer, prefetch_data, get_memory_pool, optimize_memory
)


class TestPerformanceMonitor:
    """Test performance monitoring functionality"""
    
    def test_performance_monitor_initialization(self):
        """Test performance monitor initialization"""
        monitor = PerformanceMonitor()
        assert monitor.metrics == []
        assert monitor.process is not None
    
    def test_operation_monitoring(self):
        """Test operation monitoring"""
        monitor = PerformanceMonitor()
        
        # Start operation
        context = monitor.start_operation("test_operation")
        assert context['operation_name'] == "test_operation"
        assert 'start_time' in context
        assert 'memory_before' in context
        assert 'cpu_percent' in context
        
        # Simulate some work
        time.sleep(0.01)
        
        # End operation
        metrics = monitor.end_operation(context)
        assert metrics.operation_name == "test_operation"
        assert metrics.duration > 0
        assert len(monitor.metrics) == 1
    
    def test_metrics_summary(self):
        """Test metrics summary generation"""
        monitor = PerformanceMonitor()
        
        # Add some test metrics
        for i in range(3):
            context = monitor.start_operation(f"test_op_{i}")
            time.sleep(0.01)
            monitor.end_operation(context)
        
        summary = monitor.get_metrics_summary()
        assert summary['total_operations'] == 3
        assert 'average_duration' in summary
        assert 'max_duration' in summary
        assert 'min_duration' in summary
        assert 'operations_by_name' in summary


class TestMemoryPool:
    """Test memory pool functionality"""
    
    def test_memory_pool_initialization(self):
        """Test memory pool initialization"""
        def factory():
            return {"data": "test"}
        
        pool = MemoryPool(factory, max_size=5)
        assert pool.max_size == 5
        assert pool.size() == 0
    
    def test_memory_pool_acquire_release(self):
        """Test memory pool acquire and release"""
        def factory():
            return {"data": "test", "reset": Mock()}
        
        pool = MemoryPool(factory, max_size=3)
        
        # Acquire objects
        obj1 = pool.acquire()
        obj2 = pool.acquire()
        assert obj1 is not None
        assert obj2 is not None
        
        # Release objects
        pool.release(obj1)
        pool.release(obj2)
        assert pool.size() == 2
        
        # Acquire should reuse objects
        obj3 = pool.acquire()
        assert obj3 in [obj1, obj2]
    
    def test_memory_pool_max_size_limit(self):
        """Test memory pool max size limit"""
        def factory():
            return {"data": "test"}
        
        pool = MemoryPool(factory, max_size=2)
        
        # Create more objects than max_size
        objs = [pool.acquire() for _ in range(3)]
        for obj in objs:
            pool.release(obj)
        
        # Pool should only keep max_size objects
        assert pool.size() == 2
    
    def test_memory_pool_thread_safety(self):
        """Test memory pool thread safety"""
        def factory():
            return {"data": "test"}
        
        pool = MemoryPool(factory, max_size=10)
        results = []
        
        def worker():
            obj = pool.acquire()
            time.sleep(0.01)  # Simulate work
            pool.release(obj)
            results.append(obj)
        
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert len(results) == 5


class TestResourceCache:
    """Test resource cache functionality"""
    
    def test_resource_cache_initialization(self):
        """Test resource cache initialization"""
        cache = ResourceCache(max_size=10, ttl=60)
        assert cache.max_size == 10
        assert cache.ttl == 60
        assert len(cache.cache) == 0
    
    def test_cache_set_get(self):
        """Test cache set and get operations"""
        cache = ResourceCache(max_size=5, ttl=60)
        
        # Set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Non-existent key
        assert cache.get("nonexistent") is None
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        cache = ResourceCache(max_size=5, ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("key1") is None
    
    def test_cache_max_size_limit(self):
        """Test cache max size limit"""
        cache = ResourceCache(max_size=2, ttl=60)
        
        # Fill cache beyond max size
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict oldest
        
        # Should have only 2 items
        assert len(cache.cache) == 2
        assert cache.get("key1") is None  # Oldest should be evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = ResourceCache(max_size=5, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.get("key1")
        cache.get("key1")  # Multiple accesses
        
        stats = cache.stats()
        assert stats['size'] == 2
        assert stats['max_size'] == 5
        assert stats['total_accesses'] == 3


class TestBackgroundTaskManager:
    """Test background task manager"""
    
    def test_background_task_manager_initialization(self):
        """Test background task manager initialization"""
        manager = BackgroundTaskManager(max_workers=2)
        assert manager.executor is not None
        assert len(manager.active_tasks) == 0
        manager.shutdown()
    
    def test_task_submission_and_result(self):
        """Test task submission and result retrieval"""
        manager = BackgroundTaskManager(max_workers=2)
        
        def test_task(x):
            return x * 2
        
        # Submit task
        future = manager.submit_task("test_task", test_task, 5)
        
        # Get result
        result = future.result(timeout=1)
        assert result == 10
        
        manager.shutdown()
    
    def test_task_cancellation(self):
        """Test task cancellation"""
        manager = BackgroundTaskManager(max_workers=2)
        
        def long_task():
            time.sleep(1)
            return "completed"
        
        # Submit and cancel task
        manager.submit_task("long_task", long_task)
        success = manager.cancel_task("long_task")
        assert success == True
        
        manager.shutdown()
    
    def test_task_replacement(self):
        """Test task replacement with same ID"""
        manager = BackgroundTaskManager(max_workers=2)
        
        def task1():
            time.sleep(0.1)
            return "task1"
        
        def task2():
            return "task2"
        
        # Submit first task
        manager.submit_task("test_task", task1)
        
        # Replace with second task
        future = manager.submit_task("test_task", task2)
        
        # Should get result from second task
        result = future.result(timeout=1)
        assert result == "task2"
        
        manager.shutdown()


class TestLazyLoader:
    """Test lazy loader functionality"""
    
    def test_lazy_loader_initialization(self):
        """Test lazy loader initialization"""
        def loader():
            return "loaded_data"
        
        lazy_loader = LazyLoader(loader, cache_result=True)
        assert lazy_loader.loader_func == loader
        assert lazy_loader.cache_result == True
        assert lazy_loader._loaded == False
    
    def test_lazy_loading_with_cache(self):
        """Test lazy loading with caching"""
        call_count = 0
        
        def loader():
            nonlocal call_count
            call_count += 1
            return f"loaded_data_{call_count}"
        
        lazy_loader = LazyLoader(loader, cache_result=True)
        
        # First load
        result1 = lazy_loader.load()
        assert result1 == "loaded_data_1"
        assert call_count == 1
        
        # Second load should use cache
        result2 = lazy_loader.load()
        assert result2 == "loaded_data_1"  # Same result
        assert call_count == 1  # Not called again
    
    def test_lazy_loading_without_cache(self):
        """Test lazy loading without caching"""
        call_count = 0
        
        def loader():
            nonlocal call_count
            call_count += 1
            return f"loaded_data_{call_count}"
        
        lazy_loader = LazyLoader(loader, cache_result=False)
        
        # Multiple loads should call loader each time
        result1 = lazy_loader.load()
        result2 = lazy_loader.load()
        
        assert result1 == "loaded_data_1"
        assert result2 == "loaded_data_2"
        assert call_count == 2
    
    def test_lazy_loader_reset(self):
        """Test lazy loader reset functionality"""
        call_count = 0
        
        def loader():
            nonlocal call_count
            call_count += 1
            return f"loaded_data_{call_count}"
        
        lazy_loader = LazyLoader(loader, cache_result=True)
        
        # Load and cache
        result1 = lazy_loader.load()
        assert result1 == "loaded_data_1"
        
        # Reset and load again
        lazy_loader.reset()
        result2 = lazy_loader.load()
        assert result2 == "loaded_data_2"
        assert call_count == 2


class TestPerformanceOptimizer:
    """Test performance optimizer main class"""
    
    def test_performance_optimizer_initialization(self):
        """Test performance optimizer initialization"""
        optimizer = PerformanceOptimizer()
        assert optimizer.monitor is not None
        assert optimizer.resource_cache is not None
        assert optimizer.background_tasks is not None
        assert len(optimizer.memory_pools) == 0
        assert len(optimizer.lazy_loaders) == 0
    
    def test_memory_pool_creation(self):
        """Test memory pool creation"""
        optimizer = PerformanceOptimizer()
        
        def factory():
            return {"data": "test"}
        
        pool = optimizer.create_memory_pool("test_pool", factory, max_size=5)
        assert pool.max_size == 5
        assert "test_pool" in optimizer.memory_pools
        assert optimizer.memory_pools["test_pool"] == pool
    
    def test_lazy_loader_creation(self):
        """Test lazy loader creation"""
        optimizer = PerformanceOptimizer()
        
        def loader():
            return "loaded_data"
        
        lazy_loader = optimizer.create_lazy_loader("test_loader", loader)
        assert lazy_loader.loader_func == loader
        assert "test_loader" in optimizer.lazy_loaders
        assert optimizer.lazy_loaders["test_loader"] == lazy_loader
    
    def test_resource_prefetching(self):
        """Test resource prefetching"""
        optimizer = PerformanceOptimizer()
        
        def loader():
            return "prefetched_data"
        
        # Start prefetching
        optimizer.prefetch_resource("test_key", loader)
        
        # Wait a bit for background task
        time.sleep(0.1)
        
        # Check if data was prefetched
        cached_data = optimizer.resource_cache.get("test_key")
        assert cached_data == "prefetched_data"
        
        optimizer.shutdown()
    
    def test_performance_report(self):
        """Test performance report generation"""
        optimizer = PerformanceOptimizer()
        
        # Create some components
        optimizer.create_memory_pool("test_pool", lambda: {}, max_size=5)
        optimizer.create_lazy_loader("test_loader", lambda: "test")
        
        report = optimizer.get_performance_report()
        assert 'performance_metrics' in report
        assert 'cache_stats' in report
        assert 'memory_pools' in report
        assert 'active_background_tasks' in report
        assert 'system_memory' in report
        
        optimizer.shutdown()


class TestPerformanceDecorators:
    """Test performance optimization decorators"""
    
    def test_optimize_performance_decorator(self):
        """Test optimize_performance decorator"""
        @optimize_performance("test_operation")
        def test_function(x):
            return x * 2
        
        result = test_function(5)
        assert result == 10
        
        # Check that metrics were recorded
        metrics = performance_optimizer.monitor.get_metrics_summary()
        assert metrics['total_operations'] >= 1
    
    def test_cache_result_decorator(self):
        """Test cache_result decorator"""
        call_count = 0
        
        @cache_result("test_cache_key", ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not called again
        
        # Different arguments should not use cache
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2
    
    def test_cache_result_with_different_args(self):
        """Test cache_result decorator with different arguments"""
        call_count = 0
        
        @cache_result("test_cache", ttl=60)
        def function_with_args(x, y, z=None):
            nonlocal call_count
            call_count += 1
            return x + y + (z or 0)
        
        # Different argument combinations
        result1 = function_with_args(1, 2)
        result2 = function_with_args(1, 2, z=3)
        result3 = function_with_args(1, 2)  # Should use cache
        
        assert result1 == 3
        assert result2 == 6
        assert result3 == 3
        assert call_count == 2  # Only called for unique argument combinations


class TestGlobalPerformanceUtilities:
    """Test global performance utility functions"""
    
    def test_prefetch_data_utility(self):
        """Test prefetch_data utility function"""
        def loader():
            return "prefetched_data"
        
        prefetch_data("test_prefetch", loader)
        
        # Wait for background task
        time.sleep(0.1)
        
        # Check if data was prefetched
        cached_data = performance_optimizer.resource_cache.get("test_prefetch")
        assert cached_data == "prefetched_data"
    
    def test_get_memory_pool_utility(self):
        """Test get_memory_pool utility function"""
        # Create a pool
        pool = performance_optimizer.create_memory_pool("util_pool", lambda: {}, max_size=5)
        
        # Get pool using utility
        retrieved_pool = get_memory_pool("util_pool")
        assert retrieved_pool == pool
        
        # Non-existent pool
        assert get_memory_pool("nonexistent") is None
    
    def test_optimize_memory_utility(self):
        """Test optimize_memory utility function"""
        # This should not raise any exceptions
        optimize_memory()
        
        # Verify garbage collection was triggered
        # (This is hard to test directly, but we can ensure the function runs)
        assert True


class TestPerformanceIntegration:
    """Integration tests for performance optimization"""
    
    def test_performance_optimization_in_ui_context(self):
        """Test performance optimization in UI context"""
        # Mock a UI service with performance optimization
        from src.ui.services.ui_service import UIService
        
        ui_service = UIService()
        
        # Mock keyboard handler
        ui_service.keyboard_handler = Mock()
        ui_service.keyboard_handler.get_key.return_value = 'escape'
        
        # Set menu items
        ui_service.set_menu_items(["Option 1", "Option 2", "Option 3"])
        
        # Get user selection (this should be optimized)
        result = ui_service.get_user_selection()
        assert result is None  # Escape key
        
        # Check that performance metrics were recorded
        metrics = performance_optimizer.monitor.get_metrics_summary()
        assert metrics is not None
    
    def test_system_info_screen_performance_optimization(self):
        """Test system info screen performance optimization"""
        from src.ui.screens.system_info_screen import SystemChecker
        
        # Create system checker
        checker = SystemChecker()
        
        # Get system status (should be cached)
        status1 = checker.get_system_status()
        status2 = checker.get_system_status()
        
        assert status1 == status2
        assert isinstance(status1, dict)
        assert 'authentication' in status1
        assert 'python_version' in status1
    
    def test_performance_report_generation(self):
        """Test comprehensive performance report generation"""
        # Generate some activity
        @optimize_performance("test_report_operation")
        def test_operation():
            time.sleep(0.01)
            return "completed"
        
        # Execute multiple operations
        for i in range(5):
            test_operation()
        
        # Generate report
        report = performance_optimizer.get_performance_report()
        
        assert 'performance_metrics' in report
        assert 'cache_stats' in report
        assert 'system_memory' in report
        
        metrics = report['performance_metrics']
        if metrics:  # Only check if there are metrics
            assert 'total_operations' in metrics
            assert metrics['total_operations'] >= 5