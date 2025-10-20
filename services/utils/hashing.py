"""Deterministic hashing utilities for provenance tracking."""
import hashlib
import json
from typing import Any


def sha256_file(path: str) -> str:
    """Compute SHA256 hash of a file.
    
    Args:
        path: Path to file
        
    Returns:
        Hexadecimal SHA256 hash
    """
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj: Any) -> str:
    """Compute SHA256 hash of a JSON-serializable object.
    
    Args:
        obj: Any JSON-serializable object
        
    Returns:
        Hexadecimal SHA256 hash
    """
    j = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(j).hexdigest()


def sha256_str(text: str) -> str:
    """Compute SHA256 hash of a string.
    
    Args:
        text: Input string
        
    Returns:
        Hexadecimal SHA256 hash
    """
    return hashlib.sha256(text.encode()).hexdigest()
