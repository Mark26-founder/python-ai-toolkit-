"""Exceptions for the rate_limit package.

Hierarchy
---------
RateLimitError
├── RateLimitExceededError
├── QuotaExceededError
├── InvalidRateLimitError
└── LimiterConfigurationError
"""

from __future__ import annotations


class RateLimitError(Exception):
    """Base exception for all rate-limiting errors.

    All public exceptions in this package inherit from this class, making it
    easy to catch the entire family in a single ``except`` clause.
    """


class RateLimitExceededError(RateLimitError):
    """Raised when a rate limiter rejects a request.

    Attributes:
        limit: The configured maximum requests allowed.
        window: The window duration in seconds (if applicable).
        retry_after: Suggested number of seconds to wait before retrying,
            or ``None`` if unknown.
    """

    def __init__(
        self,
        message: str,
        *,
        limit: int | None = None,
        window: float | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Initializes RateLimitExceededError.

        Args:
            message: Human-readable description of the violation.
            limit: The configured request ceiling.
            window: Window size in seconds.
            retry_after: Seconds until the caller may retry.
        """
        super().__init__(message)
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


class QuotaExceededError(RateLimitError):
    """Raised when a usage quota (hourly, daily, etc.) is exhausted.

    Attributes:
        quota: The maximum quota units allowed.
        period: A human-readable period label such as ``"daily"`` or ``"hourly"``.
        reset_at: Unix timestamp (seconds) when the quota resets, or ``None``.
    """

    def __init__(
        self,
        message: str,
        *,
        quota: int | None = None,
        period: str | None = None,
        reset_at: float | None = None,
    ) -> None:
        """Initializes QuotaExceededError.

        Args:
            message: Human-readable description of the quota violation.
            quota: The maximum allowed quota units.
            period: Label for the quota period (e.g. ``"daily"``).
            reset_at: Unix timestamp when the quota resets.
        """
        super().__init__(message)
        self.quota = quota
        self.period = period
        self.reset_at = reset_at


class InvalidRateLimitError(RateLimitError):
    """Raised when a rate limit value is logically invalid.

    Use this when a caller provides nonsensical limit parameters (e.g.
    negative request counts) rather than a misconfigured limiter object.
    """


class LimiterConfigurationError(RateLimitError):
    """Raised when a limiter object is structurally misconfigured.

    Use this during ``__init__`` validation of limiter or strategy objects,
    for example when required arguments are missing or incompatible.
    """
