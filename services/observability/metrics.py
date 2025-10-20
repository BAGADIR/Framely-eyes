"""Simple metrics collection for latency, VRAM, and error tracking."""
import time
import functools
import subprocess
from typing import Dict, Any, Callable


# Global metrics storage
METRICS: Dict[str, Any] = {
    "latency_ms": {},
    "gpu_mem_mb_peak": 0,
    "retries": 0,
    "oom_trips": 0
}


def timed(name: str) -> Callable:
    """Decorator to time function execution.
    
    Args:
        name: Metric name
        
    Returns:
        Decorated function
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            t0 = time.time()
            try:
                return await fn(*args, **kwargs)
            finally:
                elapsed_ms = 1000 * (time.time() - t0)
                METRICS["latency_ms"][name] = round(elapsed_ms, 2)
        
        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            t0 = time.time()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = 1000 * (time.time() - t0)
                METRICS["latency_ms"][name] = round(elapsed_ms, 2)
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def vram_peak() -> None:
    """Update peak VRAM usage metric."""
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
            stderr=subprocess.DEVNULL
        )
        
        # Parse output (can have multiple GPUs)
        lines = output.decode().strip().splitlines()
        memory_values = [int(line.strip()) for line in lines]
        
        if memory_values:
            max_memory = max(memory_values)
            METRICS["gpu_mem_mb_peak"] = max(METRICS["gpu_mem_mb_peak"], max_memory)
    
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        # nvidia-smi not available or failed
        pass


def reset_metrics() -> None:
    """Reset all metrics."""
    global METRICS
    METRICS = {
        "latency_ms": {},
        "gpu_mem_mb_peak": 0,
        "retries": 0,
        "oom_trips": 0
    }


def get_metrics() -> Dict[str, Any]:
    """Get current metrics snapshot.
    
    Returns:
        Metrics dictionary
    """
    return METRICS.copy()


# Fix import for async check
import asyncio
