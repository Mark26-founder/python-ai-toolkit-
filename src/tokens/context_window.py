"""Context window calculation and management."""

class ContextWindow:
    """Manages LLM context window calculations and capacity planning."""

    def __init__(self, max_tokens: int, reserved_completion_tokens: int = 0) -> None:
        """Initialize the ContextWindow manager.

        Args:
            max_tokens: The maximum total tokens supported by the context window. Must be positive.
            reserved_completion_tokens: Token capacity reserved for the model's completion response.
                Must be non-negative and less than max_tokens.

        Raises:
            ValueError: If inputs do not meet validation constraints.
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")
        if reserved_completion_tokens < 0:
            raise ValueError("reserved_completion_tokens must be non-negative.")
        if reserved_completion_tokens >= max_tokens:
            raise ValueError("reserved_completion_tokens must be less than max_tokens.")

        self.max_tokens = max_tokens
        self.reserved_completion_tokens = reserved_completion_tokens

    def remaining(self, used_tokens: int) -> int:
        """Calculate the remaining token capacity in the context window.

        Args:
            used_tokens: The number of tokens currently consumed. Must be non-negative.

        Returns:
            The number of remaining tokens available in the context window.

        Raises:
            ValueError: If used_tokens is negative.
        """
        if used_tokens < 0:
            raise ValueError("used_tokens must be non-negative.")
        return self.max_tokens - used_tokens

    def has_overflow(self, used_tokens: int) -> bool:
        """Determine if the used tokens exceed the context window maximum capacity.

        Args:
            used_tokens: The number of tokens consumed. Must be non-negative.

        Returns:
            True if used_tokens exceeds max_tokens, False otherwise.

        Raises:
            ValueError: If used_tokens is negative.
        """
        if used_tokens < 0:
            raise ValueError("used_tokens must be non-negative.")
        return used_tokens > self.max_tokens

    def available_prompt_tokens(self, used_tokens: int = 0) -> int:
        """Determine the remaining safe limit for prompt tokens.

        Accounts for both current consumption and the reserved completion tokens.

        Args:
            used_tokens: The number of prompt/system tokens already consumed. Must be non-negative.

        Returns:
            The maximum number of additional prompt tokens that can be safely sent.
            Returns 0 if current usage plus reserved space meets or exceeds capacity.

        Raises:
            ValueError: If used_tokens is negative.
        """
        if used_tokens < 0:
            raise ValueError("used_tokens must be non-negative.")
        available = self.max_tokens - self.reserved_completion_tokens - used_tokens
        return max(0, available)
