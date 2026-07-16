"""Exceptions for the prompts package."""


class PromptError(Exception):
    """Base exception for all prompt-related errors."""
    pass


class TemplateError(PromptError):
    """Raised when a template is malformed or invalid."""
    pass


class RenderError(PromptError):
    """Raised when rendering a prompt fails."""
    pass


class MessageError(PromptError):
    """Raised when a message structure or role is invalid."""
    pass


class VariableError(PromptError):
    """Raised when variables are missing, invalid, or mismatched."""
    pass
