"""Reusable validation utilities for parsed data structures."""

from typing import Any
from .exceptions import ValidationError


def _get_nested_value(data: dict[str, Any], path: str) -> Any:
    """Helper to resolve a dot-notation path in a nested dictionary.

    Args:
        data: The dictionary to search.
        path: The dot-notation path (e.g. 'user.profile.id').

    Returns:
        The resolved value.

    Raises:
        KeyError: If a key is missing.
        TypeError: If an intermediate value is not a dictionary.
    """
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            raise TypeError(f"Value at '{part}' is not a dictionary.")
        if part not in current:
            raise KeyError(part)
        current = current[part]
    return current


def validate_required_fields(data: dict[str, Any], required_fields: list[str]) -> None:
    """Validates that all required fields exist in the dataset.

    Supports nested keys via dot-notation (e.g., 'metadata.created_at').

    Args:
        data: The dictionary to validate.
        required_fields: List of expected field paths.

    Raises:
        ValidationError: If any required fields are missing.
    """
    missing = []
    for field in required_fields:
        try:
            _get_nested_value(data, field)
        except (KeyError, TypeError):
            missing.append(field)

    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")


def validate_keys(data: dict[str, Any], allowed_keys: list[str]) -> None:
    """Validates that the dictionary contains only allowed top-level keys.

    Args:
        data: The dictionary to validate.
        allowed_keys: List of permitted top-level keys.

    Raises:
        ValidationError: If any unexpected keys are found.
    """
    extra = [k for k in data.keys() if k not in allowed_keys]
    if extra:
        raise ValidationError(f"Unexpected keys: {', '.join(extra)}")


def validate_types(data: dict[str, Any], expected_types: dict[str, type | tuple[type, ...]]) -> None:
    """Validates that fields match the expected Python types.

    Supports nested keys via dot-notation.

    Args:
        data: The dictionary containing target fields.
        expected_types: A mapping of field paths to expected type or tuple of types.

    Raises:
        ValidationError: If any field matches a different type.
    """
    for path, expected_type in expected_types.items():
        try:
            val = _get_nested_value(data, path)
            if not isinstance(val, expected_type):
                actual_type = type(val).__name__
                if isinstance(expected_type, tuple):
                    expected_name = f"one of ({', '.join(t.__name__ for t in expected_type)})"
                else:
                    expected_name = expected_type.__name__
                raise ValidationError(
                    f"Field '{path}' must be of type {expected_name}, got {actual_type}."
                )
        except (KeyError, TypeError) as e:
            raise ValidationError(f"Field '{path}' could not be resolved: {e}")


def validate_enum(data: dict[str, Any], field: str, allowed_values: list[Any]) -> None:
    """Validates that a field's value belongs to a specified list of allowed values.

    Supports nested keys via dot-notation.

    Args:
        data: The dictionary containing the target field.
        field: The path to the field.
        allowed_values: Permitted values for the field.

    Raises:
        ValidationError: If the value is not in the allowed list or field is missing.
    """
    try:
        val = _get_nested_value(data, field)
        if val not in allowed_values:
            raise ValidationError(
                f"Field '{field}' value '{val}' is not one of: {allowed_values}."
            )
    except (KeyError, TypeError) as e:
        raise ValidationError(f"Field '{field}' could not be resolved: {e}")
