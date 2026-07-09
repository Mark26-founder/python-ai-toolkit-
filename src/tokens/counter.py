"""Token counting abstractions and utilities."""

from typing import Protocol, Sequence
from .models import TokenCount


class Tokenizer(Protocol):
    """Protocol defining the minimum interface required for a tokenizer."""

    def encode(self, text: str) -> Sequence[int]:
        """Encode text into a sequence of token IDs.

        Args:
            text: The text to encode.

        Returns:
            A sequence of integer token IDs.
        """
        ...




class TokenCounter:
    """A provider-independent token counter that uses an injected tokenizer."""

    def __init__(self, tokenizer: Tokenizer) -> None:
        """Initialize the token counter with a tokenizer implementation.

        Args:
            tokenizer: An object conforming to the Tokenizer Protocol.
        """
        self._tokenizer = tokenizer

    def count(self, text: str) -> TokenCount:
        """Count tokens in arbitrary text.

        Args:
            text: The string to count tokens for.

        Returns:
            A TokenCount containing token and character counts.
        """
        tokens = self._tokenizer.encode(text)
        return TokenCount(
            token_count=len(tokens),
            character_count=len(text)
        )

    def count_prompt(self, prompt: str) -> TokenCount:
        """Count tokens for a prompt string.

        Args:
            prompt: The prompt string.

        Returns:
            A TokenCount containing the count of prompt tokens.
        """
        return self.count(prompt)

    def count_completion(self, completion: str) -> TokenCount:
        """Count tokens for a completion string.

        Args:
            completion: The completion string.

        Returns:
            A TokenCount containing the count of completion tokens.
        """
        return self.count(completion)
