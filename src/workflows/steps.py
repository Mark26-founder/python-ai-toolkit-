"""Reusable workflow step abstractions.

A *step* is the smallest unit of work in a pipeline.  Steps are composable,
named, and optionally typed on both their input requirements and output
production.

Classes
-------
* :class:`StepStatus`   — enumeration of step execution outcomes.
* :class:`StepResult`   — value object carrying the outcome of one step run.
* :class:`Step`         — abstract base class for all workflow steps.
* :class:`FunctionStep` — adapter that wraps a plain callable as a step.

Design notes
------------
* :class:`Step` uses :mod:`abc` (standard library only) for enforcement.
* Input validation (:meth:`Step.validate_input`) is a hook; raise
  :class:`~workflows.exceptions.WorkflowValidationError` inside it to
  abort the step before ``execute`` is called.
* Output validation (:meth:`Step.validate_output`) runs *after* a successful
  execution and can similarly abort with a validation error.
* Steps must never communicate directly with each other; all data exchange
  goes through :class:`~workflows.context.WorkflowContext`.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .context import WorkflowContext
from .exceptions import StepExecutionError, WorkflowValidationError


# ---------------------------------------------------------------------------
# StepStatus
# ---------------------------------------------------------------------------

class StepStatus(str, Enum):
    """Execution status of a single workflow step.

    Inherits from ``str`` so status values compare equal to plain strings,
    simplifying serialisation and logging.
    """

    SUCCESS = "success"
    """The step completed without error."""

    FAILURE = "failure"
    """The step raised an unhandled exception."""

    SKIPPED = "skipped"
    """The step was intentionally bypassed (e.g. by a conditional guard)."""

    VALIDATION_FAILED = "validation_failed"
    """Input or output validation did not pass."""


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StepResult:
    """Immutable record of a single step's execution outcome.

    Attributes:
        step_name: The :attr:`Step.name` of the step that produced this result.
        status: Final :class:`StepStatus` for this execution.
        output: Optional value returned or deposited by the step.  Convention
            is to also write significant outputs into the context, but steps
            may additionally return a convenience value here.
        error: The exception instance if ``status`` is :attr:`StepStatus.FAILURE`
            or :attr:`StepStatus.VALIDATION_FAILED`; ``None`` otherwise.
        duration_seconds: Wall-clock time (seconds) spent executing the step.
        metadata: Arbitrary step-level metadata for logging or tracing.

    Example::

        result = StepResult(
            step_name="BuildPromptStep",
            status=StepStatus.SUCCESS,
            duration_seconds=0.012,
        )
    """

    step_name: str
    status: StepStatus
    output: Any = None
    error: BaseException | None = None
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Returns ``True`` when :attr:`status` is :attr:`StepStatus.SUCCESS`."""
        return self.status is StepStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Returns ``True`` when the step did not succeed."""
        return self.status in (StepStatus.FAILURE, StepStatus.VALIDATION_FAILED)

    @property
    def skipped(self) -> bool:
        """Returns ``True`` when the step was skipped."""
        return self.status is StepStatus.SKIPPED


# ---------------------------------------------------------------------------
# Step — abstract base class
# ---------------------------------------------------------------------------

class Step(ABC):
    """Abstract base class for all workflow steps.

    Subclasses must implement :meth:`execute`.  The optional hooks
    :meth:`validate_input` and :meth:`validate_output` can be overridden
    to enforce data contracts.

    Steps are *stateless*: all persistent state lives in
    :class:`~workflows.context.WorkflowContext`.  A single step instance may
    therefore be reused safely across multiple pipeline runs.

    Attributes:
        name: Human-readable step identifier.  Defaults to the class name.

    Example::

        class BuildPromptStep(Step):
            def execute(self, context: WorkflowContext) -> None:
                raw = context.get("raw_input", str)
                context.set("prompt", f"Summarise: {raw}")
    """

    def __init__(self, *, name: str | None = None) -> None:
        """Initializes Step.

        Args:
            name: Optional display name.  When ``None``, the class name is
                used.
        """
        self._name: str = name or type(self).__name__

    @property
    def name(self) -> str:
        """Returns the human-readable name of this step."""
        return self._name

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, context: WorkflowContext) -> Any:
        """Executes the step's core logic.

        Implementations should read their inputs from ``context``, perform
        their work, and write results back into ``context``.

        Args:
            context: The shared workflow context for this pipeline run.

        Returns:
            An optional convenience value.  Convention is to also write
            significant outputs into the context so downstream steps can
            access them.

        Raises:
            workflows.exceptions.StepExecutionError: On unrecoverable failures.
            workflows.exceptions.WorkflowValidationError: When produced output
                violates a declared contract.
        """
        ...  # pragma: no cover

    # ------------------------------------------------------------------
    # Validation hooks (optional overrides)
    # ------------------------------------------------------------------

    def validate_input(self, context: WorkflowContext) -> None:
        """Validates that the context contains the expected inputs.

        Called by the executor *before* :meth:`execute`.  Override this to
        enforce pre-conditions.

        Args:
            context: The shared workflow context for this pipeline run.

        Raises:
            workflows.exceptions.WorkflowValidationError: When validation
                fails.  The step will be aborted with
                :attr:`StepStatus.VALIDATION_FAILED`.
        """

    def validate_output(self, context: WorkflowContext, output: Any) -> None:
        """Validates the output produced by :meth:`execute`.

        Called by the executor *after* a successful :meth:`execute`.
        Override this to enforce post-conditions.

        Args:
            context: The shared workflow context, potentially updated by the
                step.
            output: The value returned by :meth:`execute`.

        Raises:
            workflows.exceptions.WorkflowValidationError: When validation
                fails.
        """

    # ------------------------------------------------------------------
    # Lifecycle hook
    # ------------------------------------------------------------------

    def should_skip(self, context: WorkflowContext) -> bool:
        """Determines whether this step should be skipped for this run.

        When this method returns ``True`` the executor records a
        :attr:`StepStatus.SKIPPED` result and moves on without calling
        :meth:`execute`.

        The default implementation always returns ``False``.  Override to
        implement conditional execution logic.

        Args:
            context: The shared workflow context for this pipeline run.

        Returns:
            ``True`` to skip the step, ``False`` to execute it.
        """
        return False

    # ------------------------------------------------------------------
    # Internal helpers used by executors
    # ------------------------------------------------------------------

    def run(self, context: WorkflowContext) -> StepResult:
        """Runs the full step lifecycle and returns a :class:`StepResult`.

        The lifecycle is:

        1. :meth:`should_skip` — bail out early if ``True``.
        2. :meth:`validate_input` — abort with *validation_failed* on error.
        3. :meth:`execute` — core logic.
        4. :meth:`validate_output` — abort with *validation_failed* on error.

        Any unexpected exception from ``execute`` is wrapped in a
        :class:`~workflows.exceptions.StepExecutionError` and reported as
        :attr:`StepStatus.FAILURE`.

        Args:
            context: The shared workflow context for this pipeline run.

        Returns:
            A :class:`StepResult` describing the outcome.
        """
        # --- Skip check ---
        if self.should_skip(context):
            return StepResult(step_name=self._name, status=StepStatus.SKIPPED)

        # --- Input validation ---
        try:
            self.validate_input(context)
        except WorkflowValidationError as exc:
            return StepResult(
                step_name=self._name,
                status=StepStatus.VALIDATION_FAILED,
                error=exc,
            )

        # --- Core execution ---
        start = time.perf_counter()
        try:
            output = self.execute(context)
        except (StepExecutionError, WorkflowValidationError):
            duration = time.perf_counter() - start
            raise
        except Exception as exc:
            duration = time.perf_counter() - start
            wrapped = StepExecutionError(
                f"Step {self._name!r} raised an unexpected error: {exc}",
                step_name=self._name,
                cause=exc,
            )
            return StepResult(
                step_name=self._name,
                status=StepStatus.FAILURE,
                error=wrapped,
                duration_seconds=duration,
            )
        duration = time.perf_counter() - start

        # --- Output validation ---
        try:
            self.validate_output(context, output)
        except WorkflowValidationError as exc:
            return StepResult(
                step_name=self._name,
                status=StepStatus.VALIDATION_FAILED,
                error=exc,
                duration_seconds=duration,
            )

        return StepResult(
            step_name=self._name,
            status=StepStatus.SUCCESS,
            output=output,
            duration_seconds=duration,
        )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # noqa: D105
        return f"{type(self).__name__}(name={self._name!r})"


# ---------------------------------------------------------------------------
# FunctionStep — wrap a callable as a Step
# ---------------------------------------------------------------------------

class FunctionStep(Step):
    """Adapts a plain callable into a workflow :class:`Step`.

    This allows lightweight, anonymous steps to be registered in a pipeline
    without writing a full subclass.

    Example::

        def add_greeting(context: WorkflowContext) -> None:
            name = context.get("name", str)
            context.set("greeting", f"Hello, {name}!")

        pipeline.add(FunctionStep(add_greeting, name="AddGreeting"))
    """

    def __init__(
        self,
        fn: Any,
        *,
        name: str | None = None,
    ) -> None:
        """Initializes FunctionStep.

        Args:
            fn: A callable with signature
                ``(context: WorkflowContext) -> Any``.  The callable must
                accept exactly one positional argument.
            name: Optional display name.  Defaults to the callable's
                ``__name__`` attribute, or ``"FunctionStep"`` when unavailable.
        """
        resolved_name = name or getattr(fn, "__name__", None) or "FunctionStep"
        super().__init__(name=resolved_name)
        self._fn = fn

    def execute(self, context: WorkflowContext) -> Any:
        """Delegates execution to the wrapped callable.

        Args:
            context: The shared workflow context for this pipeline run.

        Returns:
            Whatever the wrapped callable returns.
        """
        return self._fn(context)

    def __repr__(self) -> str:  # noqa: D105
        fn_name = getattr(self._fn, "__name__", repr(self._fn))
        return f"FunctionStep(name={self._name!r}, fn={fn_name!r})"
