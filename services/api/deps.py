"""FastAPI dependencies and utilities."""
import os
import redis
import torch
from typing import Optional


# Settings from environment
class Settings:
    """Application settings."""
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    STORE_PATH = os.getenv("STORE_PATH", "store")
    MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "1000"))
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MIME_WHITELIST = os.getenv("MIME_WHITELIST", "video/mp4,video/quicktime,video/x-matroska").split(",")


settings = Settings()


# Redis connection
_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Get Redis client.
    
    Returns:
        Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    return _redis_client


def check_gpu_available() -> bool:
    """Check if GPU is available.
    
    Returns:
        True if GPU available
    """
    return torch.cuda.is_available()


def check_redis_connected() -> bool:
    """Check if Redis is connected.
    
    Returns:
        True if connected
    """
    try:
        client = get_redis()
        client.ping()
        return True
    except Exception:
        return False


def check_qwen_available() -> bool:
    """Check if Qwen service is available.
    
    Returns:
        True if available
    """
    import httpx
    qwen_base = os.getenv("QWEN_API_BASE", "http://qwen:8000")
    try:
        response = httpx.get(f"{qwen_base}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False
