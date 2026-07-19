"""Exceptions for the workflows package.

Hierarchy
---------
WorkflowError
├── StepExecutionError
├── PipelineConfigurationError
├── ContextError
└── WorkflowValidationError
"""

from __future__ import annotations


class WorkflowError(Exception):
    """Base exception for all workflow-layer errors.

    All public exceptions in this package inherit from this class, allowing
    callers to catch the entire family with a single ``except WorkflowError``.

    Attributes:
        workflow_name: Optional name of the workflow or pipeline that raised
            this error.
    """

    def __init__(
        self,
        message: str,
        *,
        workflow_name: str | None = None,
    ) -> None:
        """Initializes WorkflowError.

        Args:
            message: Human-readable description of the error.
            workflow_name: Optional name of the offending workflow or pipeline.
        """
        super().__init__(message)
        self.workflow_name = workflow_name


class StepExecutionError(WorkflowError):
    """Raised when a workflow step fails during execution.

    Attributes:
        step_name: The name of the step that failed.
        step_index: Zero-based position of the step in the pipeline, or
            ``None`` when position is unavailable.
        cause: The original exception that triggered this error, if any.

    Example::

        raise StepExecutionError(
            "BuildPromptStep failed: template key missing.",
            step_name="BuildPromptStep",
            step_index=1,
            cause=original_exc,
        )
    """

    def __init__(
        self,
        message: str,
        *,
        step_name: str | None = None,
        step_index: int | None = None,
        workflow_name: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        """Initializes StepExecutionError.

        Args:
            message: Human-readable description of the failure.
            step_name: Optional name of the step that failed.
            step_index: Optional zero-based index of the step in the pipeline.
            workflow_name: Optional name of the enclosing workflow or pipeline.
            cause: The underlying exception, if any.
        """
        super().__init__(message, workflow_name=workflow_name)
        self.step_name = step_name
        self.step_index = step_index
        self.cause = cause


class PipelineConfigurationError(WorkflowError):
    """Raised when a pipeline is misconfigured.

    Use this when the pipeline structure, step ordering, or configuration
    options are invalid *before execution begins*.

    Attributes:
        workflow_name: Name of the misconfigured pipeline.

    Example::

        raise PipelineConfigurationError(
            "Pipeline 'main' has no steps registered.",
            workflow_name="main",
        )
    """


class ContextError(WorkflowError):
    """Raised when a workflow context operation fails.

    Common causes include accessing a key that does not exist, attempting to
    write to a frozen context, or type mismatches in typed storage.

    Attributes:
        key: The context key involved in the error, or ``None`` when the
            error is not key-specific.
        workflow_name: Name of the associated workflow, if known.

    Example::

        raise ContextError(
            "Key 'prompt' not found in context.",
            key="prompt",
        )
    """

    def __init__(
        self,
        message: str,
        *,
        key: str | None = None,
        workflow_name: str | None = None,
    ) -> None:
        """Initializes ContextError.

        Args:
            message: Human-readable description of the error.
            key: Optional context key involved in the failure.
            workflow_name: Optional name of the associated workflow.
        """
        super().__init__(message, workflow_name=workflow_name)
        self.key = key


class WorkflowValidationError(WorkflowError):
    """Raised when workflow-level validation fails.

    Use this to signal that a step's input or output does not meet the
    declared validation constraints, or that pipeline-level invariants are
    violated after composition.

    Attributes:
        step_name: Optional name of the step whose validation failed.
        workflow_name: Name of the associated workflow, if known.

    Example::

        raise WorkflowValidationError(
            "Step 'ParseResponse' received an empty output from the provider.",
            step_name="ParseResponse",
        )
    """

    def __init__(
        self,
        message: str,
        *,
        step_name: str | None = None,
        workflow_name: str | None = None,
    ) -> None:
        """Initializes WorkflowValidationError.

        Args:
            message: Human-readable description of the validation failure.
            step_name: Optional name of the step that failed validation.
            workflow_name: Optional name of the associated workflow.
        """
        super().__init__(message, workflow_name=workflow_name)
        self.step_name = step_name
