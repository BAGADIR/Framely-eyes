"""GPU resource pool with semaphore-based allocation."""
import asyncio
from typing import Optional


class GPUPool:
    """GPU resource pool for managing concurrent GPU tasks."""
    
    def __init__(self, max_concurrent: int = 2):
        """Initialize GPU pool.
        
        Args:
            max_concurrent: Maximum number of concurrent GPU tasks
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self._active_tasks = 0
    
    async def __aenter__(self):
        """Acquire GPU resource."""
        await self.semaphore.acquire()
        self._active_tasks += 1
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release GPU resource."""
        self.semaphore.release()
        self._active_tasks -= 1
    
    def get_active_count(self) -> int:
        """Get number of active GPU tasks.
        
        Returns:
            Number of active tasks
        """
        return self._active_tasks
    
    def get_available_count(self) -> int:
        """Get number of available GPU slots.
        
        Returns:
            Number of available slots
        """
        return self.max_concurrent - self._active_tasks


# Global GPU pool instance
_gpu_pool: Optional[GPUPool] = None


def get_gpu_pool(max_concurrent: int = 2) -> GPUPool:
    """Get or create global GPU pool.
    
    Args:
        max_concurrent: Maximum concurrent GPU tasks
        
    Returns:
        GPU pool instance
    """
    global _gpu_pool
    if _gpu_pool is None:
        _gpu_pool = GPUPool(max_concurrent)
    return _gpu_pool
