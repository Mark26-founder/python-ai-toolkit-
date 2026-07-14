"""Structured Logger implementation wrapping the Python logging module."""

from contextlib import contextmanager
import logging
import time
from typing import Any, Dict, Iterator, List, Optional, Union


class StructuredLogger:
    """Wrapper around standard Logger that simplifies structured context and timing."""

    def __init__(self, logger: logging.Logger, context: Optional[Dict[str, Any]] = None) -> None:
        """Initializes the structured logger.

        Args:
            logger: The underlying standard logging.Logger instance.
            context: In-memory context dict bound specifically to this instance.
        """
        self._logger = logger
        self._context = context or {}

    @property
    def name(self) -> str:
        """Returns the logger name."""
        return self._logger.name

    @property
    def level(self) -> int:
        """Returns the logger level."""
        return self._logger.level

    def set_level(self, level: Union[int, str]) -> None:
        """Sets the log level of the underlying logger."""
        self._logger.setLevel(level)

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """Creates a new StructuredLogger instance with merged bound metadata.

        Args:
            **kwargs: Context metadata key-values.

        Returns:
            A new StructuredLogger containing the merged context.
        """
        new_context = {**self._context, **kwargs}
        return StructuredLogger(self._logger, new_context)

    def _log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Helper to invoke underlying logging, attaching context to extra."""
        if not self._logger.isEnabledFor(level):
            return

        extra = kwargs.pop("extra", {})
        merged_extra = {**self._context, **extra}

        self._logger.log(level, msg, *args, extra=merged_extra, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs a debug message."""
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an info message."""
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs a warning message."""
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an error message."""
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs a critical message."""
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an error message with full exception traceback."""
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, *args, **kwargs)

    @contextmanager
    def time_operation(self, message: str, level: int = logging.INFO) -> Iterator[None]:
        """Context manager to time code blocks and structured log the latency.

        Args:
            message: Base log message.
            level: Logging level.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._log(
                level,
                f"{message} completed",
                extra={"elapsed_seconds": elapsed},
            )


def get_logger(name: str) -> StructuredLogger:
    """Retrieves or creates a named StructuredLogger.

    Args:
        name: Name of the logger.

    Returns:
        StructuredLogger wrapping standard library Logger.
    """
    logger = logging.getLogger(name)
    return StructuredLogger(logger)


def configure_logging(
    level: Union[int, str] = logging.INFO,
    handlers: Optional[List[logging.Handler]] = None,
) -> None:
    """Configures global settings on the root logging handler.

    Args:
        level: Minimum log level.
        handlers: Optional custom handler list to configure.
    """
    root_logger = logging.getLogger()

    # Remove existing handlers to prevent duplicate formatting output
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    root_logger.setLevel(level)

    if handlers:
        for handler in handlers:
            root_logger.addHandler(handler)
