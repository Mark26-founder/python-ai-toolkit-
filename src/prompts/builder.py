"""Fluent prompt builder for composing multi-message conversations."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .messages import Conversation, Message, Role
from .templates import PromptTemplate


@dataclass
class PromptBuilder:
    """Fluent builder for assembling structured LLM conversations.

    Provides additive methods for each conversational role and returns
    an immutable Conversation on build.
    """

    _messages: List[Message] = field(default_factory=list, init=False, repr=False)
    _variables: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def with_variables(self, **variables: Any) -> "PromptBuilder":
        """Binds shared rendering variables for use across template messages.

        Args:
            **variables: Key-value pairs to bind.

        Returns:
            Self for method chaining.
        """
        self._variables.update(variables)
        return self

    def _add(self, role: Role, content: str, name: Optional[str] = None) -> "PromptBuilder":
        self._messages.append(Message(role=role, content=content, name=name))
        return self

    def _add_from_template(
        self, role: Role, template: PromptTemplate, **overrides: Any
    ) -> "PromptBuilder":
        merged = {**self._variables, **overrides}
        content = template.render(**merged)
        return self._add(role, content)

    def system(self, content: str) -> "PromptBuilder":
        """Adds a system message.

        Args:
            content: The system instruction text.

        Returns:
            Self for method chaining.
        """
        return self._add(Role.SYSTEM, content)

    def system_template(self, template: PromptTemplate, **overrides: Any) -> "PromptBuilder":
        """Adds a system message rendered from a template.

        Args:
            template: The PromptTemplate to render.
            **overrides: Variable overrides for this message only.

        Returns:
            Self for method chaining.
        """
        return self._add_from_template(Role.SYSTEM, template, **overrides)

    def user(self, content: str) -> "PromptBuilder":
        """Adds a user message.

        Args:
            content: The user input text.

        Returns:
            Self for method chaining.
        """
        return self._add(Role.USER, content)

    def user_template(self, template: PromptTemplate, **overrides: Any) -> "PromptBuilder":
        """Adds a user message rendered from a template.

        Args:
            template: The PromptTemplate to render.
            **overrides: Variable overrides for this message only.

        Returns:
            Self for method chaining.
        """
        return self._add_from_template(Role.USER, template, **overrides)

    def assistant(self, content: str) -> "PromptBuilder":
        """Adds an assistant message.

        Args:
            content: The assistant response text.

        Returns:
            Self for method chaining.
        """
        return self._add(Role.ASSISTANT, content)

    def tool(self, content: str, name: Optional[str] = None) -> "PromptBuilder":
        """Adds a tool result message.

        Args:
            content: The tool output text.
            name: Optional tool name.

        Returns:
            Self for method chaining.
        """
        return self._add(Role.TOOL, content, name=name)

    def context(self, text: str) -> "PromptBuilder":
        """Appends a context section to the last system message, or creates one.

        Args:
            text: The contextual information to include.

        Returns:
            Self for method chaining.
        """
        section = f"Context:\n{text}"
        # Merge with existing system message if present
        if self._messages and self._messages[0].role == Role.SYSTEM:
            existing = self._messages[0]
            merged_content = f"{existing.content}\n\n{section}"
            self._messages[0] = Message(role=Role.SYSTEM, content=merged_content)
        else:
            self._messages.insert(0, Message(role=Role.SYSTEM, content=section))
        return self

    def instructions(self, text: str) -> "PromptBuilder":
        """Appends an instructions section to the system message.

        Args:
            text: The instruction content.

        Returns:
            Self for method chaining.
        """
        section = f"Instructions:\n{text}"
        if self._messages and self._messages[0].role == Role.SYSTEM:
            existing = self._messages[0]
            merged_content = f"{existing.content}\n\n{section}"
            self._messages[0] = Message(role=Role.SYSTEM, content=merged_content)
        else:
            self._messages.insert(0, Message(role=Role.SYSTEM, content=section))
        return self

    def example(self, user_text: str, assistant_text: str) -> "PromptBuilder":
        """Appends a user/assistant few-shot example pair.

        Args:
            user_text: The example user input.
            assistant_text: The expected assistant output.

        Returns:
            Self for method chaining.
        """
        self._add(Role.USER, user_text)
        self._add(Role.ASSISTANT, assistant_text)
        return self

    def build(self) -> Conversation:
        """Builds and returns an immutable Conversation from the current state.

        Returns:
            A Conversation containing all added messages.
        """
        return Conversation(messages=list(self._messages))
