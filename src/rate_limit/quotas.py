"""Deterministic quota tracking for hourly and daily usage budgets.

Quotas represent *longer-horizon* usage ceilings (hours, days) and complement
the sub-second / per-minute rate limiters in :mod:`rate_limit.limiters`.

Classes
-------
* :class:`QuotaPeriod`    — enum of supported period labels.
* :class:`QuotaBucket`    — a single-period counter with reset semantics.
* :class:`QuotaManager`   — groups multiple :class:`QuotaBucket` objects and
                             provides a unified ``acquire()`` interface.

Design principles
-----------------
* **No drift** — reset timestamps are computed from fixed anchor points
  (midnight UTC for daily; the top of the hour for hourly), not from the
  moment of first use.  This matches provider quota windows.
* **Thread-safe** — each :class:`QuotaBucket` is protected by its own
  :class:`threading.RLock`.
* **Standard library only** — :mod:`datetime` and :mod:`calendar` only.
* **Deterministic** — given the same wall-clock time, ``reset_at`` is always
  the same value regardless of when the bucket was created or last reset.

Example::

    from rate_limit.quotas import QuotaManager, QuotaBucket, QuotaPeriod

    manager = QuotaManager({
        QuotaPeriod.HOURLY: QuotaBucket(quota=1_000, period=QuotaPeriod.HOURLY),
        QuotaPeriod.DAILY:  QuotaBucket(quota=10_000, period=QuotaPeriod.DAILY),
    })

    manager.acquire()            # Consumes 1 from both buckets
    manager.acquire(units=50)    # Consumes 50 (e.g. token cost)
    print(manager.remaining())   # {QuotaPeriod.HOURLY: 949, QuotaPeriod.DAILY: 9949}
"""

from __future__ import annotations

import calendar
import threading
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Mapping

from .exceptions import LimiterConfigurationError, QuotaExceededError


# ---------------------------------------------------------------------------
# QuotaPeriod
# ---------------------------------------------------------------------------

class QuotaPeriod(str, Enum):
    """Supported quota reset periods.

    Inherits from ``str`` so values can be used directly as dict keys or
    log strings without an explicit ``.value`` lookup.
    """

    HOURLY = "hourly"
    DAILY = "daily"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_hour_utc(now: datetime) -> datetime:
    """Returns the UTC datetime of the start of the next full hour.

    Args:
        now: Current UTC-aware datetime.

    Returns:
        UTC-aware datetime at the top of the next hour.
    """
    return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)


def _next_midnight_utc(now: datetime) -> datetime:
    """Returns the UTC datetime of midnight at the start of the next day.

    Args:
        now: Current UTC-aware datetime.

    Returns:
        UTC-aware datetime at midnight of the following calendar day.
    """
    tomorrow = now.date() + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)


def _reset_at_for_period(period: QuotaPeriod) -> float:
    """Computes the Unix timestamp when the next quota reset occurs.

    Resets are anchored to calendar boundaries (top of hour, midnight UTC),
    not to the first-use timestamp, ensuring deterministic alignment with
    provider quota windows.

    Args:
        period: The :class:`QuotaPeriod` to compute a reset time for.

    Returns:
        A Unix timestamp (float, UTC) representing the next reset instant.
    """
    now = datetime.now(tz=timezone.utc)
    if period is QuotaPeriod.HOURLY:
        return _next_hour_utc(now).timestamp()
    if period is QuotaPeriod.DAILY:
        return _next_midnight_utc(now).timestamp()
    # Unreachable if all enum members are handled; kept for safety
    raise LimiterConfigurationError(f"Unsupported QuotaPeriod: {period!r}.")  # pragma: no cover


# ---------------------------------------------------------------------------
# QuotaBucket
# ---------------------------------------------------------------------------

class QuotaBucket:
    """A thread-safe counter tracking usage against a maximum quota.

    Usage is automatically reset when the current time passes ``reset_at``.
    The reset anchor is aligned to the nearest calendar boundary (top of the
    hour or midnight UTC) rather than elapsed time since creation.

    Attributes:
        quota: The maximum number of units allowed per period.
        period: The :class:`QuotaPeriod` this bucket tracks.

    Example::

        bucket = QuotaBucket(quota=1000, period=QuotaPeriod.HOURLY)
        bucket.acquire(units=10)
        print(bucket.remaining())  # 990
        print(bucket.used())       # 10
    """

    def __init__(self, quota: int, period: QuotaPeriod) -> None:
        """Initializes QuotaBucket.

        Args:
            quota: Maximum usage units allowed within the period.  Must be > 0.
            period: The reset period for this bucket.

        Raises:
            LimiterConfigurationError: If ``quota`` is not positive.
        """
        if quota <= 0:
            raise LimiterConfigurationError(
                f"quota must be a positive integer, got {quota!r}."
            )
        self._quota = quota
        self._period = period
        self._used: int = 0
        self._reset_at: float = _reset_at_for_period(period)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_reset(self) -> None:
        """Resets the counter if the current period has expired."""
        import time
        if time.time() >= self._reset_at:
            self._used = 0
            self._reset_at = _reset_at_for_period(self._period)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def quota(self) -> int:
        """The configured maximum units per period."""
        return self._quota

    @property
    def period(self) -> QuotaPeriod:
        """The reset period for this bucket."""
        return self._period

    @property
    def reset_at(self) -> float:
        """Unix timestamp (UTC) of the next quota reset.

        Returns:
            A float Unix timestamp.
        """
        with self._lock:
            return self._reset_at

    def used(self) -> int:
        """Returns the number of units consumed in the current period.

        Returns:
            Non-negative integer count of consumed units.
        """
        with self._lock:
            self._maybe_reset()
            return self._used

    def remaining(self) -> int:
        """Returns the number of remaining units in the current period.

        Returns:
            An integer in the range ``[0, quota]``.
        """
        with self._lock:
            self._maybe_reset()
            return max(0, self._quota - self._used)

    def allow(self, units: int = 1) -> bool:
        """Returns ``True`` if ``units`` can be consumed without exceeding quota.

        Args:
            units: Number of units to check.  Must be > 0.

        Returns:
            ``True`` when ``used + units <= quota``.
        """
        with self._lock:
            self._maybe_reset()
            return (self._used + units) <= self._quota

    def acquire(self, units: int = 1) -> None:
        """Consumes ``units`` from the bucket.

        Args:
            units: Number of quota units to consume.  Must be > 0.

        Raises:
            LimiterConfigurationError: If ``units`` is not positive.
            QuotaExceededError: If consuming ``units`` would exceed the quota.
        """
        if units <= 0:
            raise LimiterConfigurationError(
                f"units must be a positive integer, got {units!r}."
            )
        with self._lock:
            self._maybe_reset()
            if self._used + units > self._quota:
                raise QuotaExceededError(
                    f"{self._period.value.capitalize()} quota exceeded: "
                    f"{self._quota} units (attempted to use {units} more, "
                    f"{self._used} already consumed).",
                    quota=self._quota,
                    period=self._period.value,
                    reset_at=self._reset_at,
                )
            self._used += units

    def reset(self) -> None:
        """Manually resets the counter and advances the reset timestamp."""
        with self._lock:
            self._used = 0
            self._reset_at = _reset_at_for_period(self._period)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def reset_in_seconds(self) -> float:
        """Returns the number of seconds until the next automatic reset.

        Returns:
            Seconds remaining; ``0.0`` if the period has already expired.
        """
        import time
        with self._lock:
            return max(0.0, self._reset_at - time.time())

    def reset_at_isoformat(self) -> str:
        """Returns the next reset time as an ISO 8601 string (UTC).

        Returns:
            A string such as ``"2025-01-01T00:00:00+00:00"``.
        """
        with self._lock:
            return datetime.fromtimestamp(
                self._reset_at, tz=timezone.utc
            ).isoformat()

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"{type(self).__name__}("
            f"quota={self._quota}, "
            f"period={self._period!r}, "
            f"used={self._used})"
        )


# ---------------------------------------------------------------------------
# QuotaManager
# ---------------------------------------------------------------------------

class QuotaManager:
    """Groups multiple :class:`QuotaBucket` objects behind a unified interface.

    A single :meth:`acquire` call deducts from **all** managed buckets.  If
    any bucket is exhausted, :class:`~rate_limit.exceptions.QuotaExceededError`
    is raised and no buckets are modified.  This two-phase check-then-acquire
    is performed atomically per-bucket but not across buckets — in practice this
    is acceptable because quota windows are seconds-to-days long.

    Example::

        manager = QuotaManager({
            QuotaPeriod.HOURLY: QuotaBucket(quota=500, period=QuotaPeriod.HOURLY),
            QuotaPeriod.DAILY:  QuotaBucket(quota=5000, period=QuotaPeriod.DAILY),
        })

        manager.acquire(units=10)
        print(manager.remaining())
        # {<QuotaPeriod.HOURLY: 'hourly'>: 490, <QuotaPeriod.DAILY: 'daily'>: 4990}
    """

    def __init__(self, buckets: Mapping[QuotaPeriod, QuotaBucket]) -> None:
        """Initializes QuotaManager.

        Args:
            buckets: Mapping of :class:`QuotaPeriod` → :class:`QuotaBucket`.
                Must contain at least one entry.

        Raises:
            LimiterConfigurationError: If ``buckets`` is empty or contains
                invalid types.
        """
        if not buckets:
            raise LimiterConfigurationError("buckets must not be empty.")
        for period, bucket in buckets.items():
            if not isinstance(period, QuotaPeriod):
                raise LimiterConfigurationError(
                    f"Key {period!r} is not a QuotaPeriod instance."
                )
            if not isinstance(bucket, QuotaBucket):
                raise LimiterConfigurationError(
                    f"Value for {period!r} is not a QuotaBucket instance."
                )
        self._buckets: dict[QuotaPeriod, QuotaBucket] = dict(buckets)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self, units: int = 1) -> bool:
        """Returns ``True`` if ``units`` can be consumed from all buckets.

        Non-consuming check.

        Args:
            units: Number of units to check across every bucket.

        Returns:
            ``True`` only when every bucket reports sufficient capacity.
        """
        return all(bucket.allow(units) for bucket in self._buckets.values())

    def acquire(self, units: int = 1) -> None:
        """Consumes ``units`` from every managed bucket.

        Checks all buckets before deducting from any.  Raises on the first
        exhausted bucket without modifying any counter.

        Args:
            units: Number of units to consume.  Must be > 0.

        Raises:
            LimiterConfigurationError: If ``units`` is not positive.
            QuotaExceededError: If any bucket cannot accommodate ``units``.
        """
        if units <= 0:
            raise LimiterConfigurationError(
                f"units must be a positive integer, got {units!r}."
            )
        # Phase 1: validate all buckets
        for bucket in self._buckets.values():
            if not bucket.allow(units):
                raise QuotaExceededError(
                    f"{bucket.period.value.capitalize()} quota exceeded: "
                    f"cannot consume {units} unit(s); "
                    f"{bucket.remaining()} remaining.",
                    quota=bucket.quota,
                    period=bucket.period.value,
                    reset_at=bucket.reset_at,
                )
        # Phase 2: deduct from all buckets
        for bucket in self._buckets.values():
            bucket.acquire(units)

    def remaining(self) -> dict[QuotaPeriod, int]:
        """Returns remaining capacity for each managed bucket.

        Returns:
            Dict mapping each :class:`QuotaPeriod` to its remaining unit count.
        """
        return {period: bucket.remaining() for period, bucket in self._buckets.items()}

    def used(self) -> dict[QuotaPeriod, int]:
        """Returns consumed units for each managed bucket.

        Returns:
            Dict mapping each :class:`QuotaPeriod` to units consumed so far.
        """
        return {period: bucket.used() for period, bucket in self._buckets.items()}

    def reset(self) -> None:
        """Resets all managed buckets."""
        for bucket in self._buckets.values():
            bucket.reset()

    def reset_times(self) -> dict[QuotaPeriod, str]:
        """Returns ISO 8601 reset timestamps for all managed buckets.

        Returns:
            Dict mapping each :class:`QuotaPeriod` to an ISO 8601 string.
        """
        return {
            period: bucket.reset_at_isoformat()
            for period, bucket in self._buckets.items()
        }

    def bucket(self, period: QuotaPeriod) -> QuotaBucket:
        """Returns the :class:`QuotaBucket` for ``period``.

        Args:
            period: The period whose bucket to retrieve.

        Returns:
            The :class:`QuotaBucket` instance for that period.

        Raises:
            KeyError: If ``period`` is not managed by this manager.
        """
        return self._buckets[period]

    def __repr__(self) -> str:  # noqa: D105
        return f"QuotaManager(buckets={self._buckets!r})"
