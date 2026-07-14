"""Exceptions for the cache package."""


class CacheError(Exception):
    """Base exception for all cache-related errors."""
    pass


class CacheMissError(CacheError):
    """Raised when a key is not found in the cache."""
    pass


class CacheKeyError(CacheError):
    """Raised when a cache key cannot be generated or is invalid."""
    pass


class CacheConfigurationError(CacheError):
    """Raised when cache configuration is invalid."""
    pass


class CacheExpirationError(CacheError):
    """Raised when access is attempted on an expired cache entry."""
    pass
