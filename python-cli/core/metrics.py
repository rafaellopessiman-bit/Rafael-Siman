"""
Metrics and Performance Monitoring
"""
import threading
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional
from datetime import datetime


class OperationMetrics:
    """Track metrics for operations"""

    def __init__(self):
        self.operations = []

    def record(
        self,
        operation: str,
        duration_seconds: float,
        docs_count: Optional[int] = None,
        chunks_count: Optional[int] = None,
        status: str = "success",
    ):
        """Record an operation's metrics"""
        self.operations.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration_s": round(duration_seconds, 3),
            "docs": docs_count,
            "chunks": chunks_count,
            "status": status,
        })

    def format_message(
        self,
        operation: str,
        duration_seconds: float,
        docs_count: Optional[int] = None,
        chunks_count: Optional[int] = None,
    ) -> str:
        """Format metrics as human-readable message"""
        msg = f"[{operation}] duration={duration_seconds:.2f}s"
        if docs_count is not None:
            msg += f" docs={docs_count}"
        if chunks_count is not None:
            msg += f" chunks={chunks_count}"
        return msg

    def get_summary(self) -> dict:
        """Get summary statistics"""
        if not self.operations:
            return {}

        durations = [op["duration_s"] for op in self.operations]
        return {
            "total_operations": len(self.operations),
            "total_duration_s": sum(durations),
            "avg_duration_s": sum(durations) / len(durations),
            "min_duration_s": min(durations) if durations else 0,
            "max_duration_s": max(durations) if durations else 0,
        }


# Global metrics instance
_metrics: Optional[OperationMetrics] = None
_metrics_lock = threading.Lock()


def get_metrics() -> OperationMetrics:
    """Get global metrics instance (thread-safe)."""
    global _metrics
    if _metrics is None:
        with _metrics_lock:
            if _metrics is None:  # double-checked locking
                _metrics = OperationMetrics()
    return _metrics


def reset_metrics() -> None:
    """Reset global metrics (for testing)."""
    global _metrics
    with _metrics_lock:
        _metrics = OperationMetrics()


@contextmanager
def profile_operation(
    operation: str,
    docs_count: Optional[int] = None,
    chunks_count: Optional[int] = None,
):
    """Context manager for profiling operations

    Usage:
        with profile_operation("index", docs_count=10):
            # do indexing
            pass
    """
    metrics = get_metrics()
    
    start_time = time.perf_counter()
    status = "success"
    
    try:
        yield
    except Exception as e:
        status = "error"
        raise
    finally:
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        metrics.record(
            operation=operation,
            duration_seconds=duration,
            docs_count=docs_count,
            chunks_count=chunks_count,
            status=status,
        )


def profile_operation_decorator(func: Callable) -> Callable:
    """Decorator for profiling function execution

    Usage:
        @profile_operation_decorator
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        operation = f"{func.__module__}.{func.__name__}"
        with profile_operation(operation):
            return func(*args, **kwargs)

    return wrapper
