"""Standard logging handlers configuration and instantiation helpers."""

import logging
from logging.handlers import RotatingFileHandler
from .exceptions import HandlerError


def create_console_handler(formatter: logging.Formatter) -> logging.StreamHandler:
    """Creates a console logging handler.

    Args:
        formatter: The formatter instance to attach.

    Returns:
        A configured StreamHandler.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    return handler


def create_file_handler(filepath: str, formatter: logging.Formatter) -> logging.FileHandler:
    """Creates a file logging handler.

    Args:
        filepath: File path for the log output.
        formatter: The formatter instance to attach.

    Returns:
        A configured FileHandler.

    Raises:
        HandlerError: If the file handler cannot be created.
    """
    try:
        handler = logging.FileHandler(filepath, encoding="utf-8")
        handler.setFormatter(formatter)
        return handler
    except Exception as e:
        raise HandlerError(f"Failed to initialize file handler at '{filepath}': {e}") from e


def create_rotating_file_handler(
    filepath: str,
    formatter: logging.Formatter,
    max_bytes: int = 10485760,
    backup_count: int = 5,
) -> RotatingFileHandler:
    """Creates a rotating file logging handler.

    Args:
        filepath: File path for the log output.
        formatter: The formatter instance to attach.
        max_bytes: Maximum size in bytes before rotating. Defaults to 10MB.
        backup_count: Number of historical files to retain. Defaults to 5.

    Returns:
        A configured RotatingFileHandler.

    Raises:
        HandlerError: If the rotating file handler cannot be created.
    """
    try:
        handler = RotatingFileHandler(
            filepath, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        handler.setFormatter(formatter)
        return handler
    except Exception as e:
        raise HandlerError(
            f"Failed to initialize rotating file handler at '{filepath}': {e}"
        ) from e


def create_null_handler() -> logging.NullHandler:
    """Creates a Null handler (commonly used for libraries).

    Returns:
        A NullHandler.
    """
    return logging.NullHandler()
