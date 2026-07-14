"""Utilities for extracting structured content from text."""

import re
from .exceptions import ExtractionError


def extract_json_block(text: str) -> str:
    """Extracts the first JSON object or array from text.

    Supports markdown code fences and ignores surrounding text.

    Args:
        text: The raw text containing the JSON.

    Returns:
        The extracted JSON string.

    Raises:
        ExtractionError: If no JSON object or array is found.
    """
    # 1. Try markdown code block with/without 'json' tag
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()

    # 2. Fall back to finding first { or [ and matching last } or ]
    first_brace = text.find("{")
    first_bracket = text.find("[")

    start_idx = -1
    if first_brace != -1 and first_bracket != -1:
        start_idx = min(first_brace, first_bracket)
    elif first_brace != -1:
        start_idx = first_brace
    elif first_bracket != -1:
        start_idx = first_bracket

    if start_idx != -1:
        char = text[start_idx]
        target = "}" if char == "{" else "]"
        end_idx = text.rfind(target)
        if end_idx != -1 and end_idx > start_idx:
            return text[start_idx : end_idx + 1].strip()

    raise ExtractionError("No JSON block or object found in the text.")


def extract_code_block(text: str, language: str | None = None) -> str:
    """Extracts the first fenced code block from text.

    Args:
        text: The raw text containing code fences.
        language: Optional language filter (e.g. 'python', 'json').

    Returns:
        The content of the extracted code block.

    Raises:
        ExtractionError: If no matching code block is found.
    """
    lang_pattern = re.escape(language) if language else r"[a-zA-Z0-9_-]*"
    pattern = rf"```(?:{lang_pattern})?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    raise ExtractionError(
        f"No code block found{' for language ' + language if language else ''}."
    )


def extract_between_tags(text: str, start_tag: str, end_tag: str) -> str:
    """Extracts content between specified start and end tags.

    Args:
        text: The raw text.
        start_tag: The opening tag.
        end_tag: The closing tag.

    Returns:
        The extracted content.

    Raises:
        ExtractionError: If the start or end tags are missing or out of order.
    """
    start_idx = text.find(start_tag)
    if start_idx == -1:
        raise ExtractionError(f"Start tag '{start_tag}' not found.")

    content_start = start_idx + len(start_tag)
    end_idx = text.find(end_tag, content_start)
    if end_idx == -1:
        raise ExtractionError(f"End tag '{end_tag}' not found.")

    return text[content_start:end_idx].strip()


def extract_first_match(pattern: str, text: str) -> str:
    """Generic regex extraction helper.

    Args:
        pattern: The regular expression pattern.
        text: The text to search.

    Returns:
        The matched content. If the pattern has capture groups, returns the
        first capture group. Otherwise returns the whole match.

    Raises:
        ExtractionError: If the pattern does not match the text.
    """
    match = re.search(pattern, text)
    if not match:
        raise ExtractionError(f"Pattern '{pattern}' did not match.")
    return match.group(1) if match.groups() else match.group(0)
