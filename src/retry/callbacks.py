"""Lifecycle callback interfaces and context for retry executions."""

from dataclasses import dataclass
from typing import Any, Callable, Protocol, TypeAlias


@dataclass(frozen=True)
class RetryContext:
    """Context information passed to retry lifecycle callbacks."""
    attempt: int
    elapsed_time: float
    last_exception: Exception | None = None
    next_delay: float | None = None


class RetryCallback(Protocol):
    """Protocol defining the structural contract for retry lifecycle callbacks."""
    def __call__(self, context: RetryContext) -> Any:
        ...


# Type aliases for explicit lifecycle registration
BeforeRetryHook: TypeAlias = Callable[[RetryContext], Any]
AfterRetryHook: TypeAlias = Callable[[RetryContext], Any]
OnSuccessHook: TypeAlias = Callable[[RetryContext], Any]
OnFailureHook: TypeAlias = Callable[[RetryContext], Any]
