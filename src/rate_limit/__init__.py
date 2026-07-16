"""rate_limit — Provider-agnostic request throttling and quota enforcement.

Public API
----------
Exceptions::

    RateLimitError
    RateLimitExceededError
    QuotaExceededError
    InvalidRateLimitError
    LimiterConfigurationError

Limiters::

    FixedWindowLimiter
    SlidingWindowLimiter
    TokenBucketLimiter

Strategies::

    Limiter                  (structural Protocol)
    PerUserStrategy
    PerApiKeyStrategy
    PerEndpointStrategy
    GlobalStrategy
    CompositeStrategy

Decorators::

    rate_limited
    named_limiter
    inject_limiter
    register_limiter
    unregister_limiter
    get_limiter
    list_limiters

Quotas::

    QuotaPeriod
    QuotaBucket
    QuotaManager
"""

from __future__ import annotations

# Exceptions
from .exceptions import (
    LimiterConfigurationError,
    InvalidRateLimitError,
    QuotaExceededError,
    RateLimitError,
    RateLimitExceededError,
)

# Limiters
from .limiters import (
    FixedWindowLimiter,
    SlidingWindowLimiter,
    TokenBucketLimiter,
)

# Strategies
from .strategies import (
    CompositeStrategy,
    GlobalStrategy,
    Limiter,
    PerApiKeyStrategy,
    PerEndpointStrategy,
    PerUserStrategy,
)

# Decorators
from .decorators import (
    get_limiter,
    inject_limiter,
    list_limiters,
    named_limiter,
    rate_limited,
    register_limiter,
    unregister_limiter,
)

# Quotas
from .quotas import (
    QuotaBucket,
    QuotaManager,
    QuotaPeriod,
)

__all__ = [
    # --- Exceptions ---
    "RateLimitError",
    "RateLimitExceededError",
    "QuotaExceededError",
    "InvalidRateLimitError",
    "LimiterConfigurationError",
    # --- Limiters ---
    "FixedWindowLimiter",
    "SlidingWindowLimiter",
    "TokenBucketLimiter",
    # --- Strategies ---
    "Limiter",
    "PerUserStrategy",
    "PerApiKeyStrategy",
    "PerEndpointStrategy",
    "GlobalStrategy",
    "CompositeStrategy",
    # --- Decorators ---
    "rate_limited",
    "named_limiter",
    "inject_limiter",
    "register_limiter",
    "unregister_limiter",
    "get_limiter",
    "list_limiters",
    # --- Quotas ---
    "QuotaPeriod",
    "QuotaBucket",
    "QuotaManager",
]
