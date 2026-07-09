"""Exceptions for the tokens package."""


class TokenError(Exception):
    """Base exception for all token-related errors."""
    pass


class ContextOverflowError(TokenError):
    """Exception raised when the context window capacity is exceeded."""
    pass


class InvalidTokenBudgetError(TokenError):
    """Exception raised when a token budget configuration or operation is invalid."""
    pass


class PricingUnavailableError(TokenError):
    """Exception raised when pricing details for a given model are unavailable."""
    pass
