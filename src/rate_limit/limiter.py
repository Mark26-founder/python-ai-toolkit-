"""Core rate limiter implementations.

Provides three independent, thread-safe limiter classes:

* :class:`FixedWindowLimiter`  — simple counter reset at fixed intervals.
* :class:`SlidingWindowLimiter` — timestamp-based rolling window.
* :class:`TokenBucketLimiter`  — continuous token refill with burst support.

All classes share the same four-method public contract:

    allow()     → bool   (non-consuming peek)
    acquire()   → None   (consume or raise)
    remaining() → int    (slots / tokens left)
    reset()     → None   (restore initial state)

Time is measured with :func:`time.monotonic` throughout to guarantee
deterministic behaviour across system-clock adjustments.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque

from .exceptions import LimiterConfigurationError, RateLimitExceededError


# ---------------------------------------------------------------------------
# Protocol (structural typing reference — not enforced at runtime)
# ---------------------------------------------------------------------------

class _LimiterProtocol:  # noqa: D101  (private)
    """Informal protocol documenting the expected limiter interface."""

    def allow(self) -> bool: ...          # pragma: no cover
    def acquire(self) -> None: ...        # pragma: no cover
    def remaining(self) -> int: ...       # pragma: no cover
    def reset(self) -> None: ...          # pragma: no cover


# ---------------------------------------------------------------------------
# Fixed Window
# ---------------------------------------------------------------------------

class FixedWindowLimiter:
    """Rate limiter using a fixed time window.

    Allows up to ``max_requests`` requests within each ``window_seconds``
    period.  The window resets atomically once it expires, which can cause
    a brief burst at the boundary between two consecutive windows.

    This is the lightest-weight limiter and is appropriate when approximate
    enforcement is acceptable.

    Example::

        limiter = FixedWindowLimiter(max_requests=100, window_seconds=60)
        if limiter.allow():
            limiter.acquire()
            call_api()
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        """Initializes the FixedWindowLimiter.

        Args:
            max_requests: Maximum allowed requests per window.  Must be > 0.
            window_seconds: Duration of each window in seconds.  Must be > 0.

        Raises:
            LimiterConfigurationError: If either parameter is not positive.
        """
        if max_requests <= 0:
            raise LimiterConfigurationError(
                f"max_requests must be a positive integer, got {max_requests!r}."
            )
        if window_seconds <= 0:
            raise LimiterConfigurationError(
                f"window_seconds must be positive, got {window_seconds!r}."
            )

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._count: int = 0
        self._window_start: float = time.monotonic()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_if_needed(self) -> None:
        now = time.monotonic()
        if now - self._window_start >= self._window_seconds:
            self._count = 0
            self._window_start = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self) -> bool:
        """Returns ``True`` if a request is currently within the limit.

        This is a *non-consuming* check; it does not increment the counter.
        Use :meth:`acquire` to actually consume a slot.

        Returns:
            ``True`` when the counter has not yet reached ``max_requests``.
        """
        with self._lock:
            self._reset_if_needed()
            return self._count < self._max_requests

    def acquire(self) -> None:
        """Consumes one request slot.

        Raises:
            RateLimitExceededError: When the window is full.
        """
        with self._lock:
            self._reset_if_needed()
            if self._count >= self._max_requests:
                retry_after = self._window_seconds - (
                    time.monotonic() - self._window_start
                )
                raise RateLimitExceededError(
                    f"Fixed window limit exceeded: {self._max_requests} requests "
                    f"per {self._window_seconds}s.",
                    limit=self._max_requests,
                    window=self._window_seconds,
                    retry_after=max(0.0, retry_after),
                )
            self._count += 1

    def remaining(self) -> int:
        """Returns the number of remaining slots in the current window.

        Returns:
            An integer in the range ``[0, max_requests]``.
        """
        with self._lock:
            self._reset_if_needed()
            return max(0, self._max_requests - self._count)

    def reset(self) -> None:
        """Resets the counter and starts a fresh window immediately."""
        with self._lock:
            self._count = 0
            self._window_start = time.monotonic()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def max_requests(self) -> int:
        """The configured maximum requests per window."""
        return self._max_requests

    @property
    def window_seconds(self) -> float:
        """The configured window duration in seconds."""
        return self._window_seconds

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"{type(self).__name__}("
            f"max_requests={self._max_requests}, "
            f"window_seconds={self._window_seconds})"
        )


# ---------------------------------------------------------------------------
# Sliding Window
# ---------------------------------------------------------------------------

class SlidingWindowLimiter:
    """Rate limiter using a sliding time window.

    Keeps a deque of per-request timestamps and evicts entries older than
    ``window_seconds`` on every operation.  This provides smoother, more
    accurate enforcement than :class:`FixedWindowLimiter` at the cost of
    ``O(n)`` memory where *n* is ``max_requests``.

    Appropriate for LLM API call guards where burst spikes must be dampened
    throughout the entire window, not just at the boundary.

    Example::

        limiter = SlidingWindowLimiter(max_requests=60, window_seconds=60)
        limiter.acquire()   # raises RateLimitExceededError when full
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        """Initializes the SlidingWindowLimiter.

        Args:
            max_requests: Maximum requests allowed within the rolling window.
                Must be > 0.
            window_seconds: Width of the sliding window in seconds.  Must be > 0.

        Raises:
            LimiterConfigurationError: If either parameter is not positive.
        """
        if max_requests <= 0:
            raise LimiterConfigurationError(
                f"max_requests must be a positive integer, got {max_requests!r}."
            )
        if window_seconds <= 0:
            raise LimiterConfigurationError(
                f"window_seconds must be positive, got {window_seconds!r}."
            )

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps: Deque[float] = deque()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prune(self, now: float) -> None:
        """Remove timestamps that have fallen outside the window."""
        cutoff = now - self._window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self) -> bool:
        """Returns ``True`` if a request is currently within the limit.

        Non-consuming peek; does not record a timestamp.

        Returns:
            ``True`` when fewer than ``max_requests`` timestamps exist in the
            current window.
        """
        with self._lock:
            self._prune(time.monotonic())
            return len(self._timestamps) < self._max_requests

    def acquire(self) -> None:
        """Consumes one request slot by recording the current timestamp.

        Raises:
            RateLimitExceededError: When the sliding window is full.
        """
        with self._lock:
            now = time.monotonic()
            self._prune(now)
            if len(self._timestamps) >= self._max_requests:
                # Earliest timestamp tells us when the window will free a slot
                retry_after = (
                    self._timestamps[0] + self._window_seconds - now
                    if self._timestamps
                    else 0.0
                )
                raise RateLimitExceededError(
                    f"Sliding window limit exceeded: {self._max_requests} requests "
                    f"per {self._window_seconds}s.",
                    limit=self._max_requests,
                    window=self._window_seconds,
                    retry_after=max(0.0, retry_after),
                )
            self._timestamps.append(now)

    def remaining(self) -> int:
        """Returns remaining slots in the current window.

        Returns:
            An integer in the range ``[0, max_requests]``.
        """
        with self._lock:
            self._prune(time.monotonic())
            return max(0, self._max_requests - len(self._timestamps))

    def reset(self) -> None:
        """Clears all recorded timestamps."""
        with self._lock:
            self._timestamps.clear()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def max_requests(self) -> int:
        """The configured maximum requests per window."""
        return self._max_requests

    @property
    def window_seconds(self) -> float:
        """The configured window duration in seconds."""
        return self._window_seconds

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"{type(self).__name__}("
            f"max_requests={self._max_requests}, "
            f"window_seconds={self._window_seconds})"
        )


# ---------------------------------------------------------------------------
# Token Bucket
# ---------------------------------------------------------------------------

class TokenBucketLimiter:
    """Rate limiter using the token bucket algorithm.

    Tokens accumulate at ``refill_rate`` tokens per second up to ``capacity``.
    Each :meth:`acquire` consumes exactly one token.  The bucket starts full,
    allowing an immediate burst up to ``capacity`` before the steady-state
    rate takes effect.

    This is the most flexible algorithm and is well suited to LLM providers
    that publish per-minute and per-second token/request budgets.

    Example::

        limiter = TokenBucketLimiter(capacity=20, refill_rate=5.0)
        # Up to 20 requests immediately, then 5 per second thereafter.
        limiter.acquire()
    """

    def __init__(self, capacity: int, refill_rate: float) -> None:
        """Initializes the TokenBucketLimiter.

        Args:
            capacity: Maximum token count (burst ceiling).  Must be > 0.
            refill_rate: Tokens added per second.  Must be > 0.

        Raises:
            LimiterConfigurationError: If either parameter is not positive.
        """
        if capacity <= 0:
            raise LimiterConfigurationError(
                f"capacity must be a positive integer, got {capacity!r}."
            )
        if refill_rate <= 0:
            raise LimiterConfigurationError(
                f"refill_rate must be positive, got {refill_rate!r}."
            )

        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens: float = float(capacity)
        self._last_refill: float = time.monotonic()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self._capacity),
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self) -> bool:
        """Returns ``True`` if at least one token is available.

        Non-consuming; does not deduct a token.

        Returns:
            ``True`` when ``tokens >= 1.0`` after the latest refill.
        """
        with self._lock:
            self._refill()
            return self._tokens >= 1.0

    def acquire(self) -> None:
        """Consumes one token.

        Raises:
            RateLimitExceededError: When the bucket is empty.
        """
        with self._lock:
            self._refill()
            if self._tokens < 1.0:
                retry_after = (1.0 - self._tokens) / self._refill_rate
                raise RateLimitExceededError(
                    f"Token bucket exhausted (capacity={self._capacity}, "
                    f"refill_rate={self._refill_rate}/s).",
                    limit=self._capacity,
                    retry_after=retry_after,
                )
            self._tokens -= 1.0

    def remaining(self) -> int:
        """Returns the current number of whole tokens available.

        Returns:
            Floor of the current token count; always ``>= 0``.
        """
        with self._lock:
            self._refill()
            return int(self._tokens)

    def reset(self) -> None:
        """Refills the bucket to full capacity."""
        with self._lock:
            self._tokens = float(self._capacity)
            self._last_refill = time.monotonic()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        """The configured burst capacity."""
        return self._capacity

    @property
    def refill_rate(self) -> float:
        """The configured token refill rate (tokens per second)."""
        return self._refill_rate

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"{type(self).__name__}("
            f"capacity={self._capacity}, "
            f"refill_rate={self._refill_rate})"
        )
