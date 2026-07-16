"""Decorators for applying rate limits to synchronous functions.

Provides three decorator factories:

* :func:`rate_limited`   — attach a limiter instance directly to a function.
* :func:`named_limiter`  — look up a shared limiter from a module-level registry.
* :func:`inject_limiter` — supply the limiter at call time via a keyword argument.

All decorators raise :class:`~rate_limit.exceptions.RateLimitExceededError` when
the underlying limiter is exhausted.  They are transparent wrappers: the
decorated function's signature, name, module, qualname, annotations, and
docstring are all preserved via :func:`functools.wraps`.

Thread safety
-------------
The registry used by :func:`named_limiter` is protected by a
:class:`threading.RLock`.  Individual limiter operations are protected by their
own internal locks.

Example::

    from rate_limit.limiters import TokenBucketLimiter
    from rate_limit.decorators import rate_limited, register_limiter, named_limiter

    # Option 1 — inline limiter
    @rate_limited(TokenBucketLimiter(capacity=10, refill_rate=2.0))
    def call_llm(prompt: str) -> str:
        ...

    # Option 2 — named registry
    register_limiter("llm", TokenBucketLimiter(capacity=10, refill_rate=2.0))

    @named_limiter("llm")
    def call_llm(prompt: str) -> str:
        ...
"""

from __future__ import annotations

import threading
from functools import wraps
from typing import Any, Callable, TypeVar

from .exceptions import LimiterConfigurationError, RateLimitExceededError
from .limiters import FixedWindowLimiter, SlidingWindowLimiter, TokenBucketLimiter

# Structural typing alias for any object with an acquire() method
_AnyLimiter = FixedWindowLimiter | SlidingWindowLimiter | TokenBucketLimiter

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Named limiter registry
# ---------------------------------------------------------------------------

_registry: dict[str, Any] = {}
_registry_lock = threading.RLock()


def register_limiter(name: str, limiter: Any) -> None:
    """Registers a limiter under ``name`` in the module-level registry.

    Args:
        name: A non-empty string identifier for the limiter.
        limiter: Any object with a callable ``acquire()`` method.

    Raises:
        LimiterConfigurationError: If ``name`` is empty or ``limiter`` has no
            ``acquire`` method.
    """
    if not name:
        raise LimiterConfigurationError("Limiter name must be a non-empty string.")
    if not callable(getattr(limiter, "acquire", None)):
        raise LimiterConfigurationError(
            f"limiter {limiter!r} does not have a callable acquire() method."
        )
    with _registry_lock:
        _registry[name] = limiter


def unregister_limiter(name: str) -> None:
    """Removes a limiter from the registry.

    Args:
        name: The registered name to remove.

    Raises:
        KeyError: If ``name`` is not present in the registry.
    """
    with _registry_lock:
        if name not in _registry:
            raise KeyError(f"No limiter registered under {name!r}.")
        del _registry[name]


def get_limiter(name: str) -> Any:
    """Retrieves a limiter from the registry by name.

    Args:
        name: The registered name to look up.

    Returns:
        The registered limiter object.

    Raises:
        LimiterConfigurationError: If ``name`` is not found in the registry.
    """
    with _registry_lock:
        if name not in _registry:
            raise LimiterConfigurationError(
                f"No limiter registered under {name!r}. "
                "Call register_limiter() before using named_limiter()."
            )
        return _registry[name]


def list_limiters() -> list[str]:
    """Returns a sorted list of all registered limiter names.

    Returns:
        Alphabetically sorted list of name strings.
    """
    with _registry_lock:
        return sorted(_registry)


# ---------------------------------------------------------------------------
# rate_limited
# ---------------------------------------------------------------------------

def rate_limited(limiter: Any) -> Callable[[F], F]:
    """Decorator factory that enforces a rate limit on a synchronous function.

    Calls ``limiter.acquire()`` before every invocation of the decorated
    function.  If the limiter is exhausted, :class:`RateLimitExceededError`
    propagates without calling the function.

    Args:
        limiter: Any object with a callable ``acquire()`` method.  Typically a
            :class:`~rate_limit.limiters.FixedWindowLimiter`,
            :class:`~rate_limit.limiters.SlidingWindowLimiter`, or
            :class:`~rate_limit.limiters.TokenBucketLimiter`.

    Returns:
        A decorator that wraps a synchronous function with rate limiting.

    Raises:
        LimiterConfigurationError: If ``limiter`` lacks a callable ``acquire``.

    Example::

        @rate_limited(FixedWindowLimiter(max_requests=5, window_seconds=1))
        def ping() -> str:
            return "pong"
    """
    if not callable(getattr(limiter, "acquire", None)):
        raise LimiterConfigurationError(
            f"limiter {limiter!r} does not have a callable acquire() method."
        )

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter.acquire()
            return func(*args, **kwargs)

        # Expose the underlying limiter for introspection
        wrapper.__rate_limiter__ = limiter  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# named_limiter
# ---------------------------------------------------------------------------

def named_limiter(name: str) -> Callable[[F], F]:
    """Decorator factory that looks up a limiter by name from the registry.

    The lookup happens lazily on **each function call**, so the limiter can be
    (re-)registered after the decorator is applied.

    Args:
        name: The name of a previously registered limiter
            (see :func:`register_limiter`).

    Returns:
        A decorator that wraps a synchronous function with the named limiter.

    Raises:
        LimiterConfigurationError: At *call time* if ``name`` is not in the
            registry.

    Example::

        register_limiter("openai", TokenBucketLimiter(60, 1.0))

        @named_limiter("openai")
        def complete(prompt: str) -> str:
            ...
    """
    if not name:
        raise LimiterConfigurationError("name must be a non-empty string.")

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            lim = get_limiter(name)  # raises LimiterConfigurationError if missing
            lim.acquire()
            return func(*args, **kwargs)

        wrapper.__rate_limiter_name__ = name  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# inject_limiter
# ---------------------------------------------------------------------------

def inject_limiter(
    kwarg_name: str = "limiter",
    *,
    default: Any = None,
) -> Callable[[F], F]:
    """Decorator factory that allows callers to inject a limiter at call time.

    The decorated function gains an extra keyword argument (``kwarg_name``)
    that the decorator intercepts.  If the caller passes a limiter, its
    ``acquire()`` is called before the function executes.  If no limiter is
    provided, ``default`` is used; if ``default`` is ``None``, the call
    proceeds without rate limiting.

    The injected keyword argument is **removed** before the wrapped function is
    invoked, so the function's own signature does not need to declare it.

    Args:
        kwarg_name: Name of the keyword argument that accepts the limiter.
            Defaults to ``"limiter"``.
        default: A limiter to use when the caller does not supply one, or
            ``None`` to disable limiting by default.

    Returns:
        A decorator that wraps a synchronous function with optional limiter
        injection.

    Example::

        @inject_limiter(kwarg_name="lim")
        def fetch(url: str) -> bytes:
            ...

        # Caller injects the limiter:
        fetch("https://example.com", lim=FixedWindowLimiter(10, 1))

        # Or relies on no limiting:
        fetch("https://example.com")
    """
    if not kwarg_name:
        raise LimiterConfigurationError("kwarg_name must be a non-empty string.")

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            lim = kwargs.pop(kwarg_name, default)
            if lim is not None:
                if not callable(getattr(lim, "acquire", None)):
                    raise LimiterConfigurationError(
                        f"Injected limiter {lim!r} does not have a callable acquire()."
                    )
                lim.acquire()
            return func(*args, **kwargs)

        wrapper.__rate_limiter_kwarg__ = kwarg_name  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
