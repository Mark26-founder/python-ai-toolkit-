"""Token cost estimation based on injected pricing parameters."""

from dataclasses import dataclass
from .models import CostEstimate


@dataclass(frozen=True)
class Pricing:
    """Represents the token pricing configuration for a model."""

    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    currency: str = "USD"


class CostEstimator:
    """Calculates financial costs for token consumption based on pricing rates."""

    def __init__(self, pricing: Pricing) -> None:
        """Initialize the CostEstimator with pricing specifications.

        Args:
            pricing: The Pricing structure containing cost rates per 1,000 tokens.
        """
        self._pricing = pricing

    def estimate(self, prompt_tokens: int, completion_tokens: int) -> CostEstimate:
        """Estimate the cost of a single request.

        Args:
            prompt_tokens: Number of prompt tokens used. Must be non-negative.
            completion_tokens: Number of completion tokens used. Must be non-negative.

        Returns:
            A CostEstimate object containing detailed input, output, and total costs.

        Raises:
            ValueError: If either token count is negative.
        """
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ValueError("Token counts must be non-negative.")

        input_cost = (prompt_tokens / 1000.0) * self._pricing.input_cost_per_1k_tokens
        output_cost = (completion_tokens / 1000.0) * self._pricing.output_cost_per_1k_tokens
        total_cost = input_cost + output_cost

        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            currency=self._pricing.currency,
        )

    def estimate_monthly(
        self,
        requests_per_month: int,
        avg_prompt_tokens: int,
        avg_completion_tokens: int,
    ) -> CostEstimate:
        """Estimate the monthly token costs for a given volume of requests.

        Args:
            requests_per_month: Expected number of requests per month. Must be non-negative.
            avg_prompt_tokens: Average prompt tokens per request. Must be non-negative.
            avg_completion_tokens: Average completion tokens per request. Must be non-negative.

        Returns:
            A CostEstimate object representing the estimated monthly cost.

        Raises:
            ValueError: If any input argument is negative.
        """
        if requests_per_month < 0 or avg_prompt_tokens < 0 or avg_completion_tokens < 0:
            raise ValueError("All estimation parameters must be non-negative.")

        single_request_estimate = self.estimate(avg_prompt_tokens, avg_completion_tokens)

        return CostEstimate(
            input_cost=single_request_estimate.input_cost * requests_per_month,
            output_cost=single_request_estimate.output_cost * requests_per_month,
            total_cost=single_request_estimate.total_cost * requests_per_month,
            currency=self._pricing.currency,
        )
