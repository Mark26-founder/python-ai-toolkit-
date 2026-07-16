"""Strongly typed message models for provider-agnostic prompt construction."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from .exceptions import MessageError


class Role(str, Enum):
    """Defines standard conversational roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class Message:
    """Represents a single conversational message."""

    role: Role
    content: str
    name: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise MessageError("Message content cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the message to a plain dictionary.

        Returns:
            A dictionary suitable for provider adapter consumption.
        """
        d: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name is not None:
            d["name"] = self.name
        return d


@dataclass(frozen=True)
class Conversation:
    """An ordered, immutable collection of messages."""

    messages: List[Message] = field(default_factory=list)

    def append(self, message: Message) -> "Conversation":
        """Returns a new Conversation with the message appended.

        Args:
            message: The message to append.

        Returns:
            A new immutable Conversation instance.
        """
        return Conversation(messages=list(self.messages) + [message])

    def to_list(self) -> List[Dict[str, Any]]:
        """Serializes all messages to a list of dictionaries.

        Returns:
            A list of message dictionaries.
        """
        return [msg.to_dict() for msg in self.messages]

    def __len__(self) -> int:
        return len(self.messages)
