"""workflows — Deterministic workflow orchestration for AI pipelines.

This package orchestrates execution pipelines by composing reusable step
abstractions, a shared context, and structured execution helpers.  It is
**not** an agent framework and has no dependency on any AI provider.

Public API
----------
Exceptions::

    WorkflowError
    StepExecutionError
    PipelineConfigurationError
    ContextError
    WorkflowValidationError

Context::

    ExecutionMetadata
    WorkflowContext

Steps::

    StepStatus
    StepResult
    Step
    FunctionStep

Pipeline::

    PipelineOptions
    Pipeline

Executors::

    StepOutcome
    ExecutionSummary
    StepExecutor
    PipelineExecutor

Quickstart
----------
::

    from workflows import (
        Pipeline,
        WorkflowContext,
        PipelineExecutor,
        Step,
    )

    class BuildPromptStep(Step):
        def execute(self, context):
            raw = context.get("raw_input", str)
            context.set("prompt", f"Summarise: {raw}")

    pipeline = Pipeline(name="summarise")
    pipeline.add(BuildPromptStep())

    context = WorkflowContext(workflow_name="summarise")
    context.set("raw_input", "Long document text here...")

    executor = PipelineExecutor()
    summary = executor.run(pipeline, context)
    print(summary.succeeded)  # True
"""

from __future__ import annotations

# --- Exceptions ---
from .exceptions import (
    ContextError,
    PipelineConfigurationError,
    StepExecutionError,
    WorkflowError,
    WorkflowValidationError,
)

# --- Context ---
from .context import ExecutionMetadata, WorkflowContext

# --- Steps ---
from .steps import FunctionStep, Step, StepResult, StepStatus

# --- Pipeline ---
from .pipeline import Pipeline, PipelineOptions

# --- Executors ---
from .executors import ExecutionSummary, PipelineExecutor, StepExecutor, StepOutcome

__all__ = [
    # Exceptions
    "WorkflowError",
    "StepExecutionError",
    "PipelineConfigurationError",
    "ContextError",
    "WorkflowValidationError",
    # Context
    "ExecutionMetadata",
    "WorkflowContext",
    # Steps
    "StepStatus",
    "StepResult",
    "Step",
    "FunctionStep",
    # Pipeline
    "PipelineOptions",
    "Pipeline",
    # Executors
    "StepOutcome",
    "ExecutionSummary",
    "StepExecutor",
    "PipelineExecutor",
]
