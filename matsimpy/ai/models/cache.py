"""
Model response caching.

Provides caching functionality for AI model responses to improve performance
and reduce API calls.
"""

from typing import Dict, Any, Optional, Callable
import hashlib
import json
from functools import wraps
import time


class ResponseCache:
    """
    Cache for AI model responses.

    Provides simple in-memory caching with optional expiration.

    Examples:
        >>> cache = ResponseCache(max_size=100, ttl=3600)
        >>> cache.set("key", {"result": "data"})
        >>> result = cache.get("key")
    """

    def __init__(self, max_size: int = 1000, ttl: Optional[int] = None):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of cached items
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, operation: str, inputs: Dict[str, Any]) -> str:
        """
        Generate cache key from operation and inputs.

        Args:
            operation: Operation name
            inputs: Input parameters

        Returns:
            Cache key string
        """
        # Create deterministic key from operation and inputs
        key_data = {"operation": operation, "inputs": inputs}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, operation: str, inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached result.

        Args:
            operation: Operation name
            inputs: Input parameters

        Returns:
            Cached result or None if not found/expired
        """
        key = self._generate_key(operation, inputs)

        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check expiration
        if self.ttl and (time.time() - entry["timestamp"]) > self.ttl:
            del self._cache[key]
            return None

        return entry["result"]

    def set(
        self, operation: str, inputs: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        """
        Cache a result.

        Args:
            operation: Operation name
            inputs: Input parameters
            result: Result to cache
        """
        key = self._generate_key(operation, inputs)

        # Check size limit
        if len(self._cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = min(
                self._cache.keys(), key=lambda k: self._cache[k]["timestamp"]
            )
            del self._cache[oldest_key]

        self._cache[key] = {"result": result, "timestamp": time.time()}

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


def cached(cache: Optional[ResponseCache] = None):
    """
    Decorator for caching AI operation results.

    Args:
        cache: ResponseCache instance (creates new one if None)

    Examples:
        >>> @cached()
        ... def expensive_operation(interface, inputs):
        ...     return interface.call("operation", inputs)
    """
    if cache is None:
        cache = ResponseCache()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Extract operation and inputs from function call
            # This is a simplified version - may need adjustment per use case
            operation = kwargs.get("operation", func.__name__)
            inputs = kwargs.get("inputs", {})

            # Check cache
            cached_result = cache.get(operation, inputs)
            if cached_result is not None:
                return cached_result

            # Call function
            result = func(self, *args, **kwargs)

            # Cache result
            if isinstance(result, dict):
                cache.set(operation, inputs, result)

            return result

        return wrapper

    return decorator


__all__ = ["ResponseCache", "cached"]
