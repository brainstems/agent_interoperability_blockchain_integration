"""
Performance monitoring and optimization utilities.
"""

import time
import functools
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio


@dataclass
class PerformanceMetrics:
    """Performance metrics for a function or operation."""
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    errors: int = 0
    
    @property
    def average_time(self) -> float:
        """Calculate average execution time."""
        return self.total_time / self.call_count if self.call_count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "name": self.name,
            "call_count": self.call_count,
            "total_time": self.total_time,
            "average_time": self.average_time,
            "min_time": self.min_time if self.min_time != float('inf') else 0.0,
            "max_time": self.max_time,
            "errors": self.errors
        }


class PerformanceMonitor:
    """
    Monitor and track performance metrics across the system.
    
    Provides decorators and utilities for measuring execution time,
    tracking call counts, and identifying performance bottlenecks.
    """
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self._lock = asyncio.Lock()
        
    def measure(self, name: Optional[str] = None):
        """
        Decorator to measure function performance.
        
        Args:
            name: Optional custom name for the metric
            
        Example:
            @monitor.measure("process_task")
            def process_task(task_id):
                # Task processing logic
                pass
        """
        def decorator(func: Callable) -> Callable:
            metric_name = name or f"{func.__module__}.{func.__name__}"
            
            if metric_name not in self.metrics:
                self.metrics[metric_name] = PerformanceMetrics(name=metric_name)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self._update_metrics(metric_name, execution_time, error=False)
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._update_metrics(metric_name, execution_time, error=True)
                    raise
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self._update_metrics(metric_name, execution_time, error=False)
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._update_metrics(metric_name, execution_time, error=True)
                    raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    def _update_metrics(self, name: str, execution_time: float, error: bool = False):
        """Update metrics for a function call."""
        metrics = self.metrics[name]
        metrics.call_count += 1
        metrics.total_time += execution_time
        metrics.min_time = min(metrics.min_time, execution_time)
        metrics.max_time = max(metrics.max_time, execution_time)
        if error:
            metrics.errors += 1
    
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Args:
            name: Optional specific metric name
            
        Returns:
            Dictionary of metrics
        """
        if name:
            return self.metrics.get(name, PerformanceMetrics(name=name)).to_dict()
        
        return {
            name: metrics.to_dict()
            for name, metrics in self.metrics.items()
        }
    
    def get_slowest_operations(self, limit: int = 10) -> list:
        """
        Get the slowest operations by average time.
        
        Args:
            limit: Number of operations to return
            
        Returns:
            List of (name, average_time) tuples
        """
        sorted_metrics = sorted(
            self.metrics.items(),
            key=lambda x: x[1].average_time,
            reverse=True
        )
        
        return [
            (name, metrics.average_time)
            for name, metrics in sorted_metrics[:limit]
        ]
    
    def get_most_called(self, limit: int = 10) -> list:
        """
        Get the most frequently called operations.
        
        Args:
            limit: Number of operations to return
            
        Returns:
            List of (name, call_count) tuples
        """
        sorted_metrics = sorted(
            self.metrics.items(),
            key=lambda x: x[1].call_count,
            reverse=True
        )
        
        return [
            (name, metrics.call_count)
            for name, metrics in sorted_metrics[:limit]
        ]
    
    def reset(self, name: Optional[str] = None):
        """
        Reset metrics.
        
        Args:
            name: Optional specific metric to reset, or all if None
        """
        if name:
            if name in self.metrics:
                self.metrics[name] = PerformanceMetrics(name=name)
        else:
            self.metrics.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all performance metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.metrics:
            return {
                "total_operations": 0,
                "total_calls": 0,
                "total_time": 0.0,
                "total_errors": 0
            }
        
        total_calls = sum(m.call_count for m in self.metrics.values())
        total_time = sum(m.total_time for m in self.metrics.values())
        total_errors = sum(m.errors for m in self.metrics.values())
        
        return {
            "total_operations": len(self.metrics),
            "total_calls": total_calls,
            "total_time": total_time,
            "average_time_per_call": total_time / total_calls if total_calls > 0 else 0.0,
            "total_errors": total_errors,
            "error_rate": total_errors / total_calls if total_calls > 0 else 0.0,
            "slowest_operations": self.get_slowest_operations(5),
            "most_called": self.get_most_called(5)
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def measure_performance(name: Optional[str] = None):
    """
    Convenience decorator using the global performance monitor.
    
    Args:
        name: Optional custom name for the metric
        
    Example:
        @measure_performance("critical_operation")
        async def critical_operation():
            # Operation logic
            pass
    """
    return performance_monitor.measure(name)


class PerformanceContext:
    """
    Context manager for measuring performance of code blocks.
    
    Example:
        with PerformanceContext("data_processing") as perf:
            # Process data
            pass
        
        print(f"Execution time: {perf.execution_time}")
    """
    
    def __init__(self, name: str, monitor: Optional[PerformanceMonitor] = None):
        """
        Initialize performance context.
        
        Args:
            name: Name for the operation
            monitor: Optional custom monitor, uses global if None
        """
        self.name = name
        self.monitor = monitor or performance_monitor
        self.start_time: Optional[float] = None
        self.execution_time: Optional[float] = None
        
    def __enter__(self):
        """Enter the context."""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and record metrics."""
        self.execution_time = time.time() - self.start_time
        
        if self.name not in self.monitor.metrics:
            self.monitor.metrics[self.name] = PerformanceMetrics(name=self.name)
        
        self.monitor._update_metrics(
            self.name,
            self.execution_time,
            error=exc_type is not None
        )
        
        return False  # Don't suppress exceptions
