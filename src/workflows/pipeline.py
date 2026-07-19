"""Deterministic sequential workflow pipeline.

The :class:`Pipeline` manages an ordered registry of :class:`~workflows.steps.Step`
instances and drives their execution against a shared
:class:`~workflows.context.WorkflowContext`.

Classes
-------
* :class:`PipelineOptions` — configuration options for pipeline execution.
* :class:`Pipeline`        — ordered step registry with validation and execution.

Design notes
------------
* Steps are executed strictly in registration order (deterministic).
* When ``stop_on_failure=True`` (default), the first failed step halts the
  run; subsequent steps are not executed.
* When ``stop_on_failure=False``, all steps run regardless of prior failures
  and the caller inspects the returned :class:`~workflows.executors.ExecutionSummary`.
* Pipeline validation (``validate()``) checks structural correctness before
  the first run; it does **not** execute steps.
* The pipeline is reentrant: the same instance may be run multiple times
  with different :class:`~workflows.context.WorkflowContext` objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .context import WorkflowContext
from .exceptions import PipelineConfigurationError, StepExecutionError
from .steps import Step, StepResult, StepStatus


# ---------------------------------------------------------------------------
# PipelineOptions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineOptions:
    """Immutable configuration options for a :class:`Pipeline` run.

    Attributes:
        stop_on_failure: When ``True`` (default), the pipeline aborts after
            the first step that produces a non-success status.  When
            ``False``, all registered steps are executed regardless of
            intermediate failures.
        raise_on_failure: When ``True`` (default), the pipeline re-raises the
            underlying :class:`~workflows.exceptions.StepExecutionError` after
            recording it.  Set to ``False`` to collect all results without
            raising, even when ``stop_on_failure`` is ``True``.
        step_metadata: Arbitrary per-run metadata forwarded into each
            :class:`~workflows.steps.StepResult` ``metadata`` dict for
            observability.

    Example::

        opts = PipelineOptions(stop_on_failure=False, raise_on_failure=False)
    """

    stop_on_failure: bool = True
    raise_on_failure: bool = True
    step_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """Ordered registry and executor for workflow steps.

    Steps are registered via :meth:`add` and executed sequentially by
    :meth:`run`.  The pipeline is reentrant: the same instance can run
    multiple times with different contexts.

    Attributes are private; the public API consists solely of :meth:`add`,
    :meth:`remove`, :meth:`validate`, :meth:`run`, :meth:`steps`,
    :meth:`step_count`, and :meth:`clear`.

    Example::

        pipeline = Pipeline(name="rag-pipeline")
        pipeline.add(LoadConfigStep())
        pipeline.add(BuildPromptStep())
        pipeline.add(CallProviderStep())

        context = WorkflowContext(workflow_name="rag-pipeline")
        results = pipeline.run(context)
    """

    def __init__(
        self,
        *,
        name: str = "pipeline",
        options: PipelineOptions | None = None,
    ) -> None:
        """Initializes Pipeline.

        Args:
            name: Human-readable name for this pipeline.  Propagated into
                exception messages and execution summaries.
            options: Default :class:`PipelineOptions` for every :meth:`run`
                call.  Individual calls may override these by passing their
                own ``options`` argument.
        """
        self._name = name
        self._default_options = options or PipelineOptions()
        self._steps: list[Step] = []

    # ------------------------------------------------------------------
    # Step registration
    # ------------------------------------------------------------------

    def add(self, step: Step) -> "Pipeline":
        """Appends ``step`` to the end of the execution sequence.

        Duplicate step instances are allowed; each occurrence executes
        independently at its registered position.

        Args:
            step: Any :class:`~workflows.steps.Step` instance.

        Returns:
            ``self`` to enable fluent chaining::

                pipeline.add(StepA()).add(StepB()).add(StepC())

        Raises:
            PipelineConfigurationError: If ``step`` is ``None`` or not a
                :class:`~workflows.steps.Step` instance.
        """
        if not isinstance(step, Step):
            raise PipelineConfigurationError(
                f"Expected a Step instance, got {type(step).__name__!r}.",
                workflow_name=self._name,
            )
        self._steps.append(step)
        return self

    def add_many(self, steps: list[Step]) -> "Pipeline":
        """Appends multiple steps in order.

        Equivalent to calling :meth:`add` for each element.

        Args:
            steps: Ordered list of :class:`~workflows.steps.Step` instances.

        Returns:
            ``self`` for fluent chaining.
        """
        for step in steps:
            self.add(step)
        return self

    def remove(self, step_name: str) -> bool:
        """Removes the *first* step with :attr:`~workflows.steps.Step.name`
        equal to ``step_name``.

        Args:
            step_name: The name to search for.

        Returns:
            ``True`` if a step was found and removed; ``False`` otherwise.
        """
        for i, step in enumerate(self._steps):
            if step.name == step_name:
                self._steps.pop(i)
                return True
        return False

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Returns the human-readable name of this pipeline."""
        return self._name

    @property
    def steps(self) -> list[Step]:
        """Returns a snapshot (copy) of the registered step list.

        Returns:
            Ordered list of :class:`~workflows.steps.Step` instances.
        """
        return list(self._steps)

    @property
    def step_count(self) -> int:
        """Returns the number of registered steps."""
        return len(self._steps)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Validates the pipeline structure prior to execution.

        Checks performed:

        * At least one step is registered.
        * No two steps share the same name (duplicate names create ambiguity
          in summaries and logs).

        Raises:
            PipelineConfigurationError: When any validation check fails.

        Example::

            pipeline.validate()  # call before the first run in production
        """
        if not self._steps:
            raise PipelineConfigurationError(
                f"Pipeline {self._name!r} has no steps registered.",
                workflow_name=self._name,
            )

        seen: set[str] = set()
        duplicates: list[str] = []
        for step in self._steps:
            if step.name in seen:
                duplicates.append(step.name)
            seen.add(step.name)

        if duplicates:
            raise PipelineConfigurationError(
                f"Pipeline {self._name!r} has duplicate step names: "
                f"{sorted(set(duplicates))!r}.  "
                "Each step must have a unique name.",
                workflow_name=self._name,
            )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(
        self,
        context: WorkflowContext,
        *,
        options: PipelineOptions | None = None,
    ) -> list[StepResult]:
        """Executes all registered steps sequentially.

        Steps are invoked in registration order.  For each step the full
        lifecycle defined by :meth:`~workflows.steps.Step.run` is executed
        (skip check → input validation → execute → output validation).

        Args:
            context: Shared :class:`~workflows.context.WorkflowContext` for
                this run.  The context is mutated in-place as steps deposit
                results.
            options: Optional per-call options that override the pipeline
                defaults for this invocation only.

        Returns:
            An ordered list of :class:`~workflows.steps.StepResult` objects,
            one per step that was attempted (excluding steps that were never
            reached due to ``stop_on_failure``).

        Raises:
            PipelineConfigurationError: If the pipeline has no steps
                registered.
            StepExecutionError: When a step fails and both
                ``stop_on_failure`` and ``raise_on_failure`` are ``True``.

        Example::

            context = WorkflowContext(workflow_name="rag-pipeline")
            results = pipeline.run(context)
            for r in results:
                print(r.step_name, r.status, r.duration_seconds)
        """
        if not self._steps:
            raise PipelineConfigurationError(
                f"Pipeline {self._name!r} has no steps registered.",
                workflow_name=self._name,
            )

        effective_options = options or self._default_options
        results: list[StepResult] = []

        for index, step in enumerate(self._steps):
            result = step.run(context)

            # Attach step_index to metadata for observability
            if effective_options.step_metadata or index is not None:
                enriched_meta = {
                    "step_index": index,
                    **effective_options.step_metadata,
                    **result.metadata,
                }
                # Re-create as a new frozen StepResult with enriched metadata
                result = StepResult(
                    step_name=result.step_name,
                    status=result.status,
                    output=result.output,
                    error=result.error,
                    duration_seconds=result.duration_seconds,
                    metadata=enriched_meta,
                )

            results.append(result)

            if result.failed and effective_options.stop_on_failure:
                if effective_options.raise_on_failure and result.error is not None:
                    if isinstance(result.error, StepExecutionError):
                        raise result.error
                    raise StepExecutionError(
                        f"Pipeline {self._name!r} aborted at step "
                        f"{step.name!r} (index {index}).",
                        step_name=step.name,
                        step_index=index,
                        workflow_name=self._name,
                        cause=result.error,
                    )
                break

        return results

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Removes all registered steps from the pipeline."""
        self._steps.clear()

    def __len__(self) -> int:  # noqa: D105
        return len(self._steps)

    def __repr__(self) -> str:  # noqa: D105
        step_names = [s.name for s in self._steps]
        return f"Pipeline(name={self._name!r}, steps={step_names!r})"
