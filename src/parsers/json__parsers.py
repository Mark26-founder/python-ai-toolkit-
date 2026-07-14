"""Utilities for safely parsing and repairing JSON strings."""

import json
import re
from typing import Any
from .exceptions import JSONParseError


def parse_json(json_str: str) -> Any:
    """Parses a JSON string strictly.

    Args:
        json_str: The JSON string to parse.

    Returns:
        The parsed Python object (dict, list, etc.).

    Raises:
        JSONParseError: If parsing fails.
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise JSONParseError(f"Failed to parse JSON: {e}") from e


def parse_json_safe(json_str: str) -> Any | None:
    """Parses a JSON string safely, returning None on failure.

    Args:
        json_str: The JSON string to parse.

    Returns:
        The parsed Python object, or None if parsing fails.
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def repair_json(text: str) -> str:
    """Deterministically repairs common LLM mistakes in JSON formatting.

    Handles:
    - Surrounding markdown code fences.
    - Leading/trailing conversational text.
    - Trailing commas in objects or arrays.
    - Excess whitespace.

    Args:
        text: The raw, potentially malformed JSON text.

    Returns:
        The repaired JSON string.
    """
    cleaned = text.strip()

    # 1. Strip outermost markdown code fences if they wrap the entire text
    cleaned = re.sub(r"^```(?:json)?\s*([\s\S]*?)\s*```$", r"\1", cleaned).strip()

    # 2. Strip leading/trailing conversational text by finding the first brace/bracket
    first_brace = cleaned.find("{")
    first_bracket = cleaned.find("[")

    start_idx = -1
    if first_brace != -1 and first_bracket != -1:
        start_idx = min(first_brace, first_bracket)
    elif first_brace != -1:
        start_idx = first_brace
    elif first_bracket != -1:
        start_idx = first_bracket

    if start_idx != -1:
        char = cleaned[start_idx]
        target = "}" if char == "{" else "]"
        end_idx = cleaned.rfind(target)
        if end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx : end_idx + 1]

    # 3. Remove trailing commas in objects and arrays
    # e.g., {"key": "val",} -> {"key": "val"}
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

    return cleaned.strip()
