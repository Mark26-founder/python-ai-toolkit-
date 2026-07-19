"""Workflow context object for sharing state between pipeline steps.

The :class:`WorkflowContext` is the single conduit through which steps
exchange data without being directly coupled to each other.  Steps read
inputs from the context and write outputs back into it after they execute.

Classes
-------
* :class:`ExecutionMetadata` — immutable snapshot of workflow-level metadata.
* :class:`WorkflowContext`   — mutable, typed key-value store with metadata.

Design notes
------------
* Metadata (run ID, workflow name, start time) is frozen after construction.
* Data storage is mutable so steps can deposit results incrementally.
* Typed accessors raise :class:`~workflows.exceptions.ContextError` rather
  than generic ``KeyError`` or ``TypeError`` to maintain exception uniformity.
* No thread-safety is provided intentionally; pipelines run sequentially and
  a single context instance is never shared across concurrent threads.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, TypeVar

from .exceptions import ContextError

T = TypeVar("T")


# ---------------------------------------------------------------------------
# ExecutionMetadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionMetadata:
    """Immutable metadata captured at workflow start time.

    Attributes:
        run_id: A unique identifier for this specific execution run.
            Defaults to a randomly generated UUID4 string.
        workflow_name: A human-readable name for the pipeline being executed.
        started_at: Unix timestamp (seconds) recorded when the context was
            created.
        tags: Arbitrary string tags for filtering or logging purposes.
        extra: Caller-supplied metadata that does not fit a named field.

    Example::

        meta = ExecutionMetadata(workflow_name="rag-pipeline")
        print(meta.run_id)     # e.g. "3e4d7f2a-..."
        print(meta.started_at) # e.g. 1720000000.123
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = "unnamed"
    started_at: float = field(default_factory=time.time)
    tags: tuple[str, ...] = field(default_factory=tuple)
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# WorkflowContext
# ---------------------------------------------------------------------------

class WorkflowContext:
    """A typed, mutable key-value store shared across all steps in a pipeline.

    Steps deposit results and retrieve inputs exclusively through this object,
    avoiding direct dependencies on one another.

    The context is not thread-safe.  It is designed to live for the duration
    of a single synchronous pipeline execution.

    Attributes:
        metadata: Immutable :class:`ExecutionMetadata` captured at
            construction time.

    Example::

        ctx = WorkflowContext(workflow_name="rag-pipeline")
        ctx.set("prompt", "Summarise the document.")
        prompt = ctx.get("prompt", str)
    """

    def __init__(
        self,
        *,
        workflow_name: str = "unnamed",
        run_id: str | None = None,
        tags: tuple[str, ...] = (),
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Initializes WorkflowContext.

        Args:
            workflow_name: Human-readable name for the enclosing workflow.
            run_id: Optional run identifier.  A UUID4 is generated when
                ``None``.
            tags: Optional string tags attached to this run.
            extra: Optional extra metadata forwarded to
                :class:`ExecutionMetadata`.
        """
        meta_kwargs: dict[str, Any] = {
            "workflow_name": workflow_name,
            "tags": tags,
            "extra": extra or {},
        }
        if run_id is not None:
            meta_kwargs["run_id"] = run_id

        self._metadata: ExecutionMetadata = ExecutionMetadata(**meta_kwargs)
        self._store: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> ExecutionMetadata:
        """Returns the immutable execution metadata for this run."""
        return self._metadata

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Stores ``value`` under ``key``.

        Args:
            key: Non-empty string identifier for the value.
            value: Any Python object to store.

        Raises:
            ContextError: If ``key`` is empty.

        Example::

            ctx.set("parsed_response", response_object)
        """
        if not key:
            raise ContextError(
                "Context key must be a non-empty string.",
                key=key,
                workflow_name=self._metadata.workflow_name,
            )
        self._store[key] = value

    def get(self, key: str, expected_type: type[T] | None = None) -> T:
        """Retrieves the value stored under ``key``.

        Args:
            key: The key to look up.
            expected_type: When provided, the retrieved value is validated
                against this type using ``isinstance``.  Pass ``None`` to
                skip type checking and return ``Any``.

        Returns:
            The stored value, narrowed to ``expected_type`` when supplied.

        Raises:
            ContextError: If ``key`` is absent from the store.
            ContextError: If the stored value does not match ``expected_type``.

        Example::

            prompt = ctx.get("prompt", str)
        """
        if key not in self._store:
            raise ContextError(
                f"Key {key!r} not found in workflow context.",
                key=key,
                workflow_name=self._metadata.workflow_name,
            )
        value = self._store[key]
        if expected_type is not None and not isinstance(value, expected_type):
            raise ContextError(
                f"Context key {key!r} has type {type(value).__name__!r}, "
                f"expected {expected_type.__name__!r}.",
                key=key,
                workflow_name=self._metadata.workflow_name,
            )
        return value  # type: ignore[return-value]

    def get_or_default(self, key: str, default: T) -> T:
        """Retrieves ``key`` or returns ``default`` if absent.

        Unlike :meth:`get`, this method never raises :class:`ContextError`
        for missing keys.

        Args:
            key: The key to look up.
            default: Value returned when ``key`` is absent.

        Returns:
            The stored value, or ``default``.

        Example::

            cache_hit = ctx.get_or_default("cache_result", None)
        """
        return self._store.get(key, default)  # type: ignore[return-value]

    def has(self, key: str) -> bool:
        """Returns ``True`` if ``key`` is present in the store.

        Args:
            key: The key to check.

        Returns:
            Boolean indicating presence.
        """
        return key in self._store

    def delete(self, key: str) -> None:
        """Removes ``key`` from the store if it exists.

        This is a no-op when ``key`` is absent; callers do not need to check
        :meth:`has` before calling.

        Args:
            key: The key to remove.
        """
        self._store.pop(key, None)

    def keys(self) -> list[str]:
        """Returns a sorted list of all keys currently in the store.

        Returns:
            Alphabetically sorted list of key strings.
        """
        return sorted(self._store)

    def snapshot(self) -> dict[str, Any]:
        """Returns a shallow copy of the current store contents.

        The returned dict is independent of the context; mutations to it
        do not affect the live store.

        Returns:
            Shallow copy of the internal key-value store.
        """
        return dict(self._store)

    def update(self, data: dict[str, Any]) -> None:
        """Merges ``data`` into the store, overwriting existing keys.

        Args:
            data: Mapping of keys and values to store.

        Raises:
            ContextError: If any key in ``data`` is an empty string.
        """
        for key, value in data.items():
            self.set(key, value)

    def clear_data(self) -> None:
        """Removes all data from the store.

        Metadata is not affected.  Useful for resetting a context between
        test executions.
        """
        self._store.clear()

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __contains__(self, key: object) -> bool:  # noqa: D105
        return key in self._store

    def __len__(self) -> int:  # noqa: D105
        return len(self._store)

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"WorkflowContext("
            f"workflow_name={self._metadata.workflow_name!r}, "
            f"run_id={self._metadata.run_id!r}, "
            f"keys={self.keys()!r})"
        )
