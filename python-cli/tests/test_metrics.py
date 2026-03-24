"""
Tests for Metrics and Monitoring
"""
import time
import pytest

from src.core.metrics import (
    get_metrics,
    reset_metrics,
    profile_operation,
    profile_operation_decorator,
    OperationMetrics,
)


def test_operation_metrics_record():
    """Test recording metrics"""
    metrics = OperationMetrics()
    
    metrics.record("index", duration_seconds=1.5, docs_count=10)
    
    assert len(metrics.operations) == 1
    assert metrics.operations[0]["operation"] == "index"
    assert metrics.operations[0]["duration_s"] == 1.5
    assert metrics.operations[0]["docs"] == 10


def test_operation_metrics_format():
    """Test formatting metrics message"""
    metrics = OperationMetrics()
    
    msg = metrics.format_message("index", duration_seconds=2.0, docs_count=5)
    
    assert "[index]" in msg
    assert "duration=2.00s" in msg
    assert "docs=5" in msg


def test_profile_operation_context_manager():
    """Test profile_operation context manager"""
    reset_metrics()
    metrics = get_metrics()
    
    with profile_operation("test_op", docs_count=3):
        time.sleep(0.01)  # Simulate work
    
    assert len(metrics.operations) == 1
    assert metrics.operations[0]["operation"] == "test_op"
    assert metrics.operations[0]["docs"] == 3
    assert metrics.operations[0]["duration_s"] >= 0.009  # Allow for timing precision


def test_profile_operation_handles_exceptions():
    """Test that profile_operation records errors"""
    reset_metrics()
    metrics = get_metrics()
    
    try:
        with profile_operation("failing_op"):
            raise ValueError("Test error")
    except ValueError:
        pass
    
    assert len(metrics.operations) == 1
    assert metrics.operations[0]["status"] == "error"


def test_profile_operation_decorator():
    """Test decorator for profiling"""
    reset_metrics()
    metrics = get_metrics()
    
    @profile_operation_decorator
    def test_function():
        time.sleep(0.01)
        return "result"
    
    result = test_function()
    
    assert result == "result"
    assert len(metrics.operations) == 1
    assert "test_function" in metrics.operations[0]["operation"]


def test_metrics_summary():
    """Test metrics summary statistics"""
    reset_metrics()
    metrics = get_metrics()
    
    # Record multiple operations
    metrics.record("op1", duration_seconds=1.0)
    metrics.record("op2", duration_seconds=2.0)
    metrics.record("op3", duration_seconds=3.0)
    
    summary = metrics.get_summary()
    
    assert summary["total_operations"] == 3
    assert summary["total_duration_s"] == 6.0
    assert summary["avg_duration_s"] == 2.0


def test_metrics_global_singleton():
    """Test that get_metrics returns same instance"""
    reset_metrics()
    
    metrics1 = get_metrics()
    metrics1.record("op1", duration_seconds=1.0)
    
    metrics2 = get_metrics()
    
    assert metrics1 is metrics2
    assert len(metrics2.operations) == 1
