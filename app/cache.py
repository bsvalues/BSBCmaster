"""
This module provides caching utilities for the API.
"""

import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, cast

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variable for generic function
F = TypeVar('F', bound=Callable[..., Any])

# Global cache storage
# Structure: {key: (value, expiry_timestamp)}
_cache: Dict[str, Tuple[Any, float]] = {}

def cache(ttl_seconds: int = 300):
    """
    Cache decorator for function results.
    
    Args:
        ttl_seconds: Time to live in seconds for cached results
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            # Check if result is in cache and not expired
            if cache_key in _cache:
                value, expiry = _cache[cache_key]
                if time.time() < expiry:
                    logger.debug(f"Cache hit for {cache_key}")
                    return value
                else:
                    # Remove expired cache entry
                    logger.debug(f"Cache expired for {cache_key}")
                    del _cache[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, time.time() + ttl_seconds)
            logger.debug(f"Cached result for {cache_key} with TTL {ttl_seconds}s")
            
            return result
        return cast(F, wrapper)
    return decorator

def invalidate_cache(prefix: Optional[str] = None):
    """
    Invalidate cache entries with the given prefix or all if prefix is None.
    
    Args:
        prefix: Optional prefix to match cache keys
    """
    global _cache
    if prefix:
        # Remove cache entries that start with the prefix
        keys_to_remove = [k for k in _cache.keys() if k.startswith(prefix)]
        for k in keys_to_remove:
            del _cache[k]
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries with prefix '{prefix}'")
    else:
        # Clear the entire cache
        _cache.clear()
        logger.info("Invalidated all cache entries")

def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the current cache.
    
    Returns:
        Dictionary with cache statistics
    """
    current_time = time.time()
    total_entries = len(_cache)
    valid_entries = sum(1 for _, expiry in _cache.values() if current_time < expiry)
    expired_entries = total_entries - valid_entries
    
    # Calculate memory usage (rough estimate)
    memory_usage = sum(len(str(value)) + 8 for value, _ in _cache.values())  # 8 bytes for timestamp
    
    return {
        "total_entries": total_entries,
        "valid_entries": valid_entries,
        "expired_entries": expired_entries,
        "memory_usage_bytes": memory_usage,
        "timestamp": datetime.utcnow().isoformat()
    }