"""Decorators for caching and memoizing function outputs."""

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast
from .cache import Cache
from .keys import generate_key

F = TypeVar("F", bound=Callable[..., Any])


def cached(cache_instance: Cache, ttl: Optional[float] = None) -> Callable[[F], F]:
    """Decorator to cache function results inside a shared Cache instance.

    Args:
        cache_instance: The Cache object to store results in.
        ttl: Optional custom TTL override.

    Returns:
        The decorated function.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Prefix key with the function name to avoid collisions across functions
            key = generate_key(func.__module__, func.__name__, *args, **kwargs)
            if cache_instance.contains(key):
                return cache_instance.get(key)

            result = func(*args, **kwargs)
            cache_instance.set(key, result, ttl=ttl)
            return result

        return cast(F, wrapper)

    return decorator


def memoize(max_size: Optional[int] = None, ttl: Optional[float] = None) -> Callable[[F], F]:
    """Decorator to memoize a function with an internal local Cache.

    Args:
        max_size: Maximum cache capacity.
        ttl: Expiration duration in seconds.

    Returns:
        The decorated function.
    """
    cache_instance = Cache(max_size=max_size, default_ttl=ttl)
    return cached(cache_instance, ttl=ttl)
