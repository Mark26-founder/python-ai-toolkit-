"""Token budgeting and allocation management."""

from .exceptions import InvalidTokenBudgetError


class TokenBudgetManager:
    """Manages token budgets, allocations, and consumption limits."""

    def __init__(self, total_budget: int, reserved_completion_tokens: int = 0) -> None:
        """Initialize the TokenBudgetManager.

        Args:
            total_budget: The maximum allowed token limit. Must be positive.
            reserved_completion_tokens: Token count reserved for completions.
                Must be non-negative and less than total_budget.

        Raises:
            InvalidTokenBudgetError: If inputs do not meet configuration constraints.
        """
        if total_budget <= 0:
            raise InvalidTokenBudgetError("total_budget must be greater than zero.")
        if reserved_completion_tokens < 0:
            raise InvalidTokenBudgetError("reserved_completion_tokens must be non-negative.")
        if reserved_completion_tokens >= total_budget:
            raise InvalidTokenBudgetError(
                "reserved_completion_tokens must be less than total_budget."
            )

        self.total_budget = total_budget
        self.reserved_completion_tokens = reserved_completion_tokens

    def remaining(self, consumed_tokens: int) -> int:
        """Calculate the remaining tokens in the budget.

        Args:
            consumed_tokens: The number of tokens already consumed. Must be non-negative.

        Returns:
            The number of remaining tokens in the budget. Can be negative if budget is exceeded.

        Raises:
            InvalidTokenBudgetError: If consumed_tokens is negative.
        """
        if consumed_tokens < 0:
            raise InvalidTokenBudgetError("consumed_tokens must be non-negative.")
        return self.total_budget - consumed_tokens

    def within_budget(self, consumed_tokens: int) -> bool:
        """Check if the consumed tokens are within the total budget limit.

        Args:
            consumed_tokens: The number of tokens consumed. Must be non-negative.

        Returns:
            True if consumed_tokens does not exceed total_budget, False otherwise.

        Raises:
            InvalidTokenBudgetError: If consumed_tokens is negative.
        """
        if consumed_tokens < 0:
            raise InvalidTokenBudgetError("consumed_tokens must be non-negative.")
        return consumed_tokens <= self.total_budget

    def available_prompt_tokens(self, consumed_tokens: int = 0) -> int:
        """Determine the remaining budget available for prompt tokens.

        Accounts for both current consumption and the reserved completion tokens.

        Args:
            consumed_tokens: The number of tokens already consumed. Must be non-negative.

        Returns:
            The number of additional prompt tokens available within budget.
            Returns 0 if usage plus reservation meets or exceeds budget.

        Raises:
            InvalidTokenBudgetError: If consumed_tokens is negative.
        """
        if consumed_tokens < 0:
            raise InvalidTokenBudgetError("consumed_tokens must be non-negative.")
        available = self.total_budget - self.reserved_completion_tokens - consumed_tokens
        return max(0, available)
