"""Provider-agnostic response models.

All response types are regular (mutable) :func:`dataclasses.dataclass`
instances; they are produced by adapters and consumed by callers, so
immutability is less critical here than for request models.  Fields that
may differ between providers carry an explicit ``Any`` type or are wrapped in
a ``dict[str, Any]`` metadata bag.

Classes
-------
* :class:`FinishReason`      — enumeration of generation stop reasons.
* :class:`Usage`             — token-consumption accounting.
* :class:`ChatResponse`      — result of a chat-completion call.
* :class:`EmbeddingResponse` — result of an embedding call.
* :class:`ImageData`         — a single generated image.
* :class:`ImageResponse`     — result of an image-generation call.

Design notes
------------
* All dataclasses use ``@dataclass(slots=True)`` (Python 3.10+) for
  memory efficiency without sacrificing readability.
* ``Usage`` tracks both input and output tokens and an optional total so
  adapters that report only a total can still populate the model.
* ``metadata`` dicts on every response type are the escape hatch for
  provider-specific fields (e.g. ``system_fingerprint``, ``logprobs``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# FinishReason
# ---------------------------------------------------------------------------

class FinishReason(str, Enum):
    """Reasons why a model stopped generating tokens.

    Inherits from ``str`` for easy serialisation and string comparison.
    """

    STOP = "stop"
    """Natural end of generation; the model chose to stop."""

    LENGTH = "length"
    """Generation was cut off by ``max_tokens``."""

    CONTENT_FILTER = "content_filter"
    """Output was blocked or modified by the provider's safety system."""

    TOOL_CALL = "tool_call"
    """The model produced a tool / function call instead of a text response."""

    ERROR = "error"
    """Generation was terminated due to a provider-side error."""

    UNKNOWN = "unknown"
    """Reason is not mapped to a known value; inspect ``metadata``."""

    @classmethod
    def from_raw(cls, value: str) -> FinishReason:
        """Maps a raw provider string to the closest :class:`FinishReason`.

        Args:
            value: The finish reason string returned by the provider.

        Returns:
            The matching :class:`FinishReason`, or :attr:`UNKNOWN` when the
            value cannot be mapped.
        """
        normalised = value.lower().replace("-", "_")
        try:
            return cls(normalised)
        except ValueError:
            return cls.UNKNOWN


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Usage:
    """Token consumption accounting for a single API call.

    Providers that do not distinguish between prompt and completion tokens
    may set only ``total_tokens``.

    Attributes:
        prompt_tokens: Number of tokens in the input / prompt.
        completion_tokens: Number of tokens in the generated output.
        total_tokens: Sum of prompt and completion tokens.  If ``None``,
            callers can compute it as ``prompt_tokens + completion_tokens``.
        metadata: Provider-specific usage extensions (e.g. cached token
            counts, audio token counts).

    Example::

        usage = Usage(prompt_tokens=120, completion_tokens=80, total_tokens=200)
        print(usage.total_tokens)  # 200
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def effective_total(self) -> int:
        """Returns the effective total token count.

        Returns:
            ``total_tokens`` if set, otherwise ``prompt_tokens + completion_tokens``.
        """
        if self.total_tokens is not None:
            return self.total_tokens
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: Usage) -> Usage:
        """Combines two :class:`Usage` instances into an aggregate.

        Args:
            other: Another :class:`Usage` to add to this one.

        Returns:
            A new :class:`Usage` with summed token counts.
        """
        if not isinstance(other, Usage):
            return NotImplemented  # type: ignore[return-value]
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=(self.effective_total() + other.effective_total()),
        )


# ---------------------------------------------------------------------------
# ChatResponse
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ChatResponse:
    """The result of a chat-completion API call.

    Attributes:
        content: The text of the assistant's reply.  May be empty when
            ``finish_reason`` is :attr:`FinishReason.TOOL_CALL`.
        model: The model identifier that actually produced the response
            (may differ from the requested model due to routing).
        finish_reason: Why the model stopped generating.
        usage: Token consumption accounting.
        provider: The name of the provider that served the request.
        response_id: An opaque ID assigned by the provider, useful for
            debugging or feedback submission.
        metadata: Provider-specific fields not captured by the above.

    Example::

        response = ChatResponse(
            content="Rate limiting controls request throughput.",
            model="gpt-4o",
            finish_reason=FinishReason.STOP,
            usage=Usage(prompt_tokens=20, completion_tokens=10),
            provider="openai",
        )
    """

    content: str
    model: str
    finish_reason: FinishReason = FinishReason.STOP
    usage: Usage = field(default_factory=Usage)
    provider: str = ""
    response_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Returns ``True`` when generation ended naturally or at token limit."""
        return self.finish_reason in {FinishReason.STOP, FinishReason.LENGTH}

    @property
    def has_tool_call(self) -> bool:
        """Returns ``True`` when the response carries a tool call."""
        return self.finish_reason is FinishReason.TOOL_CALL


# ---------------------------------------------------------------------------
# EmbeddingResponse
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EmbeddingResponse:
    """The result of an embedding API call.

    Attributes:
        embeddings: A list of embedding vectors, one per input string.  Each
            vector is a ``list[float]``.
        model: The model that produced the embeddings.
        dimensions: The dimensionality of the output vectors.
        usage: Token consumption accounting.
        provider: The name of the provider that served the request.
        metadata: Provider-specific fields.

    Example::

        response = EmbeddingResponse(
            embeddings=[[0.1, -0.3, 0.9]],
            model="text-embedding-3-small",
            dimensions=3,
            usage=Usage(prompt_tokens=4),
            provider="openai",
        )
    """

    embeddings: list[list[float]]
    model: str
    dimensions: int = 0
    usage: Usage = field(default_factory=Usage)
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.dimensions == 0 and self.embeddings:
            # Auto-detect dimensionality from the first vector
            object.__setattr__(self, "dimensions", len(self.embeddings[0]))


# ---------------------------------------------------------------------------
# ImageData
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ImageData:
    """A single generated image within an :class:`ImageResponse`.

    Attributes:
        url: An HTTP URL pointing to the generated image, or ``None`` when
            the image is delivered as base-64 data.
        b64_json: Base-64-encoded image bytes, or ``None`` when the image is
            delivered as a URL.
        revised_prompt: The actual prompt used after any provider-side
            rewriting, or ``None`` if unchanged.
        metadata: Provider-specific fields (e.g. seed, safety ratings).
    """

    url: str | None = None
    b64_json: str | None = None
    revised_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.url is None and self.b64_json is None:
            raise ValueError(
                "ImageData must have either 'url' or 'b64_json' set."
            )

    @property
    def is_url(self) -> bool:
        """``True`` when the image is available as a URL."""
        return self.url is not None

    @property
    def is_inline(self) -> bool:
        """``True`` when the image is available as inline base-64 data."""
        return self.b64_json is not None


# ---------------------------------------------------------------------------
# ImageResponse
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ImageResponse:
    """The result of an image-generation API call.

    Attributes:
        images: Ordered list of generated images.
        model: The model that produced the images.
        provider: The name of the provider that served the request.
        metadata: Provider-specific fields (e.g. request ID, safety info).

    Example::

        response = ImageResponse(
            images=[ImageData(url="https://example.com/img/abc.png")],
            model="dall-e-3",
            provider="openai",
        )
    """

    images: list[ImageData]
    model: str
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.images:
            raise ValueError("ImageResponse.images must contain at least one ImageData.")

    @property
    def first(self) -> ImageData:
        """Convenience accessor for the first generated image.

        Returns:
            The first :class:`ImageData` in the response.
        """
        return self.images[0]
