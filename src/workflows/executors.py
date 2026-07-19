"""Reusable execution helpers for pipelines and individual steps.

This module provides thin, deterministic wrappers around
:class:`~workflows.pipeline.Pipeline` and :class:`~workflows.steps.Step`
execution.  They add timing, error aggregation, and a structured summary
object without coupling to any AI provider or orchestration framework.

Classes
-------
* :class:`StepOutcome`       — per-step timing and error record (lightweight).
* :class:`ExecutionSummary`  — aggregated summary of a complete pipeline run.
* :class:`StepExecutor`      — runs a single step in isolation.
* :class:`PipelineExecutor`  — runs a full pipeline and produces a summary.

Design notes
------------
* :class:`PipelineExecutor` wraps :meth:`~workflows.pipeline.Pipeline.run`
  and enriches the results with wall-clock timing at the run level.
* :class:`StepExecutor` is useful for testing and exploratory debugging
  where you want to exercise one step independently.
* Both executors are stateless; instantiate once and call repeatedly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .context import WorkflowContext
from .exceptions import StepExecutionError, WorkflowError
from .pipeline import Pipeline, PipelineOptions
from .steps import Step, StepResult, StepStatus


# ---------------------------------------------------------------------------
# StepOutcome
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StepOutcome:
    """Lightweight per-step record stored inside :class:`ExecutionSummary`.

    This is derived from :class:`~workflows.steps.StepResult` but strips the
    raw output value to keep summaries serialisation-friendly.

    Attributes:
        step_name: Display name of the step.
        status: Final :class:`~workflows.steps.StepStatus`.
        duration_seconds: Wall-clock time spent in the step.
        error_message: String representation of the error, or ``None``.
        metadata: Step-level metadata forwarded from :class:`~workflows.steps.StepResult`.
    """

    step_name: str
    status: StepStatus
    duration_seconds: float = 0.0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Returns ``True`` when :attr:`status` is :attr:`~workflows.steps.StepStatus.SUCCESS`."""
        return self.status is StepStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Returns ``True`` when the step did not succeed."""
        return self.status in (StepStatus.FAILURE, StepStatus.VALIDATION_FAILED)

    @classmethod
    def from_result(cls, result: StepResult) -> "StepOutcome":
        """Constructs a :class:`StepOutcome` from a :class:`~workflows.steps.StepResult`.

        Args:
            result: The step result to convert.

        Returns:
            A :class:`StepOutcome` derived from ``result``.
        """
        return cls(
            step_name=result.step_name,
            status=result.status,
            duration_seconds=result.duration_seconds,
            error_message=str(result.error) if result.error is not None else None,
            metadata=dict(result.metadata),
        )


# ---------------------------------------------------------------------------
# ExecutionSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionSummary:
    """Aggregated summary of a complete pipeline run.

    Attributes:
        workflow_name: Name of the pipeline that was executed.
        run_id: Unique run identifier, sourced from the context metadata.
        total_duration_seconds: Wall-clock time for the entire run.
        outcomes: Ordered list of :class:`StepOutcome` objects, one per
            executed step.
        errors: List of all :class:`BaseException` instances collected from
            failed steps (regardless of ``stop_on_failure`` setting).
        succeeded: ``True`` when all executed steps succeeded.

    Example::

        summary = executor.run(pipeline, context)
        print(summary.succeeded)
        for outcome in summary.outcomes:
            print(f"{outcome.step_name}: {outcome.status} ({outcome.duration_seconds:.3f}s)")
    """

    workflow_name: str
    run_id: str
    total_duration_seconds: float
    outcomes: tuple[StepOutcome, ...]
    errors: tuple[BaseException, ...]

    @property
    def succeeded(self) -> bool:
        """Returns ``True`` when no step failed or was validation-rejected."""
        return not any(o.failed for o in self.outcomes)

    @property
    def failed_steps(self) -> list[StepOutcome]:
        """Returns all outcomes with a non-success status."""
        return [o for o in self.outcomes if o.failed]

    @property
    def skipped_steps(self) -> list[StepOutcome]:
        """Returns all outcomes with :attr:`~workflows.steps.StepStatus.SKIPPED` status."""
        return [o for o in self.outcomes if o.status is StepStatus.SKIPPED]

    @property
    def step_count(self) -> int:
        """Returns the total number of steps that were attempted."""
        return len(self.outcomes)

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"ExecutionSummary("
            f"workflow_name={self.workflow_name!r}, "
            f"succeeded={self.succeeded}, "
            f"steps={self.step_count}, "
            f"duration={self.total_duration_seconds:.3f}s)"
        )


# ---------------------------------------------------------------------------
# StepExecutor
# ---------------------------------------------------------------------------

class StepExecutor:
    """Executes a single workflow step in isolation.

    Useful for unit-testing individual steps without constructing a full
    pipeline.  The executor is stateless and may be reused.

    Example::

        executor = StepExecutor()
        context = WorkflowContext(workflow_name="test")
        context.set("raw_input", "hello world")

        result = executor.run(step, context)
        print(result.status, result.duration_seconds)
    """

    def run(self, step: Step, context: WorkflowContext) -> StepResult:
        """Executes ``step`` against ``context`` and returns the result.

        Delegates to :meth:`~workflows.steps.Step.run` so the full lifecycle
        (skip → validate_input → execute → validate_output) is honoured.

        Args:
            step: The :class:`~workflows.steps.Step` to execute.
            context: The shared workflow context.

        Returns:
            A :class:`~workflows.steps.StepResult` describing the outcome.
        """
        return step.run(context)


# ---------------------------------------------------------------------------
# PipelineExecutor
# ---------------------------------------------------------------------------

class PipelineExecutor:
    """Runs a full :class:`~workflows.pipeline.Pipeline` and produces an
    :class:`ExecutionSummary`.

    The executor adds wall-clock timing at the run level and aggregates all
    errors, even when ``stop_on_failure=False``.

    Example::

        executor = PipelineExecutor()
        context = WorkflowContext(workflow_name="rag-pipeline")
        summary = executor.run(pipeline, context)

        if not summary.succeeded:
            for err in summary.errors:
                logging.error("Step failed: %s", err)
    """

    def run(
        self,
        pipeline: Pipeline,
        context: WorkflowContext,
        *,
        options: PipelineOptions | None = None,
    ) -> ExecutionSummary:
        """Executes ``pipeline`` and returns an :class:`ExecutionSummary`.

        This method catches :class:`~workflows.exceptions.StepExecutionError`
        (and its parent :class:`~workflows.exceptions.WorkflowError`) raised
        by the pipeline when ``raise_on_failure=True``, records them in the
        summary, and re-raises.  When ``raise_on_failure=False`` no exception
        propagates.

        Args:
            pipeline: The :class:`~workflows.pipeline.Pipeline` to execute.
            context: Shared :class:`~workflows.context.WorkflowContext` for
                this run.
            options: Optional per-call :class:`~workflows.pipeline.PipelineOptions`
                forwarded to the pipeline.

        Returns:
            An :class:`ExecutionSummary` regardless of whether the run
            succeeded or failed.

        Raises:
            StepExecutionError: Propagated from the pipeline when
                ``raise_on_failure=True`` and a step fails.
        """
        start = time.perf_counter()
        results: list[StepResult] = []
        raised: BaseException | None = None

        try:
            results = pipeline.run(context, options=options)
        except (StepExecutionError, WorkflowError) as exc:
            raised = exc
            # Reconstruct as much result data as possible from what was
            # collected before the exception.  pipeline.run accumulates
            # results up to and including the failing step, then raises.
            # We cannot recover more results here, so proceed with partial.

        duration = time.perf_counter() - start

        # Collect errors from results AND the raised exception
        all_errors: list[BaseException] = []
        for r in results:
            if r.error is not None:
                all_errors.append(r.error)
        if raised is not None and raised not in all_errors:
            all_errors.append(raised)

        summary = ExecutionSummary(
            workflow_name=pipeline.name,
            run_id=context.metadata.run_id,
            total_duration_seconds=duration,
            outcomes=tuple(StepOutcome.from_result(r) for r in results),
            errors=tuple(all_errors),
        )

        if raised is not None:
            raise raised

        return summary

    def run_safe(
        self,
        pipeline: Pipeline,
        context: WorkflowContext,
        *,
        options: PipelineOptions | None = None,
    ) -> ExecutionSummary:
        """Executes ``pipeline`` and always returns a summary, never raises.

        Internally uses ``PipelineOptions(raise_on_failure=False)`` so all
        step failures are captured in the summary without propagating.
        Caller-supplied ``options`` are merged with ``raise_on_failure``
        forced to ``False``.

        Args:
            pipeline: The :class:`~workflows.pipeline.Pipeline` to execute.
            context: Shared :class:`~workflows.context.WorkflowContext` for
                this run.
            options: Optional per-call options.  ``raise_on_failure`` is
                overridden to ``False`` regardless of what is passed.

        Returns:
            An :class:`ExecutionSummary` describing the run outcome.
        """
        base = options or PipelineOptions()
        safe_options = PipelineOptions(
            stop_on_failure=base.stop_on_failure,
            raise_on_failure=False,
            step_metadata=base.step_metadata,
        )

        start = time.perf_counter()
        try:
            results = pipeline.run(context, options=safe_options)
        except (StepExecutionError, WorkflowError) as exc:
            # Should not happen with raise_on_failure=False, but guard anyway.
            duration = time.perf_counter() - start
            return ExecutionSummary(
                workflow_name=pipeline.name,
                run_id=context.metadata.run_id,
                total_duration_seconds=duration,
                outcomes=(),
                errors=(exc,),
            )

        duration = time.perf_counter() - start

        all_errors: list[BaseException] = [
            r.error for r in results if r.error is not None
        ]
        return ExecutionSummary(
            workflow_name=pipeline.name,
            run_id=context.metadata.run_id,
            total_duration_seconds=duration,
            outcomes=tuple(StepOutcome.from_result(r) for r in results),
            errors=tuple(all_errors),
        )
