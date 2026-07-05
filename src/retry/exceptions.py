"""Exceptions for the retry package."""

class RetryError(Exception):
    """Base exception for all errors raised by the retry package."""
    def __init__(self, message: str) -> None:
        super().__init__(message)


class RetryConfigurationError(RetryError):
    """Raised when an invalid retry policy or configuration is provided."""
    pass


class MaxRetriesExceededError(RetryError):
    """Raised when an operation fails permanently after reaching the maximum retry attempts."""
    def __init__(self, message: str, total_attempts: int, last_exception: Exception | None = None) -> None:
        super().__init__(message)
        self.total_attempts = total_attempts
        self.last_exception = last_exception
