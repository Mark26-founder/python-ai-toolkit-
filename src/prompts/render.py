"""Prompt rendering: variable substitution, formatting, and message generation."""

from typing import Any, Dict, List
from .exceptions import RenderError, VariableError
from .messages import Conversation, Message, Role
from .templates import PromptTemplate


def render_template(template: PromptTemplate, **variables: Any) -> str:
    """Renders a PromptTemplate with the provided variables.

    Args:
        template: The PromptTemplate to render.
        **variables: Variable values for substitution.

    Returns:
        The rendered string.

    Raises:
        VariableError: If required variables are missing.
        RenderError: If rendering fails unexpectedly.
    """
    try:
        return template.render(**variables)
    except VariableError:
        raise
    except Exception as e:
        raise RenderError(f"Failed to render template: {e}") from e


def render_message(role: Role, template: PromptTemplate, **variables: Any) -> Message:
    """Renders a PromptTemplate and wraps it as a typed Message.

    Args:
        role: The conversational role for this message.
        template: The PromptTemplate to render.
        **variables: Variable values for substitution.

    Returns:
        A Message with the rendered content.
    """
    content = render_template(template, **variables)
    return Message(role=role, content=content)


def render_conversation(
    message_specs: List[Dict[str, Any]],
    variables: Dict[str, Any],
) -> Conversation:
    """Renders an ordered list of message specifications into a Conversation.

    Each specification is a dict with:
        - ``role``: a Role enum value or string.
        - ``template``: a PromptTemplate instance.

    Args:
        message_specs: List of dicts describing each message.
        variables: Shared variable pool for all templates.

    Returns:
        A fully rendered Conversation.

    Raises:
        RenderError: If a spec is malformed.
    """
    conversation = Conversation()
    for spec in message_specs:
        try:
            role = spec["role"] if isinstance(spec["role"], Role) else Role(spec["role"])
            template: PromptTemplate = spec["template"]
        except (KeyError, ValueError) as e:
            raise RenderError(f"Malformed message specification: {e}") from e

        message = render_message(role, template, **variables)
        conversation = conversation.append(message)

    return conversation


def format_prompt(messages: Conversation, separator: str = "\n\n") -> str:
    """Serializes a Conversation to a plain text prompt string.

    Useful for single-string APIs that do not support the chat format.

    Args:
        messages: The Conversation to format.
        separator: Delimiter between messages.

    Returns:
        A formatted multi-turn prompt string.
    """
    parts = []
    for msg in messages.messages:
        parts.append(f"{msg.role.value.upper()}: {msg.content}")
    return separator.join(parts)
