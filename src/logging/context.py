"""Utilities for managing request-scoped logging context using contextvars."""

import contextvars
import uuid
from typing import Any, Dict, Optional

# Async and thread-safe local logging context storage
_LOG_CONTEXT: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "log_context", default={}
)


def get_context() -> Dict[str, Any]:
    """Retrieves the current active logging context.

    Returns:
        A dictionary copy of the active context metadata.
    """
    return dict(_LOG_CONTEXT.get())


def set_context(context: Dict[str, Any]) -> None:
    """Replaces the active logging context with the provided dictionary.

    Args:
        context: The new context metadata.
    """
    _LOG_CONTEXT.set(dict(context))


def clear_context() -> None:
    """Clears the current logging context."""
    _LOG_CONTEXT.set({})


def bind_context(**kwargs: Any) -> None:
    """Adds metadata fields to the current logging context.

    Args:
        **kwargs: Context metadata key-value pairs.
    """
    ctx = get_context()
    ctx.update(kwargs)
    set_context(ctx)


def unbind_context(*keys: str) -> None:
    """Removes specified keys from the current logging context.

    Args:
        *keys: Key names to unbind.
    """
    ctx = get_context()
    for key in keys:
        ctx.pop(key, None)
    set_context(ctx)


class LogContext:
    """Context manager and decorator for temporary logging context scoping."""

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the scoped context metadata state.

        Args:
            **kwargs: Metadatum bindings.
        """
        self.new_context = kwargs
        self.token: Optional[contextvars.Token[Dict[str, Any]]] = None

    def __enter__(self) -> Dict[str, Any]:
        """Merges new metadata and returns the active context."""
        current = get_context()
        merged = {**current, **self.new_context}
        self.token = _LOG_CONTEXT.set(merged)
        return merged

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Resets the context to its state before entering."""
        if self.token:
            _LOG_CONTEXT.reset(self.token)


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Binds a correlation ID to the logging context.

    Args:
        correlation_id: The correlation ID string. Generates a UUID4 if None.

    Returns:
        The set correlation ID.
    """
    cid = correlation_id or str(uuid.uuid4())
    bind_context(correlation_id=cid)
    return cid
