"""Validation functions for configuration datasets."""

from typing import Any, Callable, Dict, List, Tuple, Union
from .exceptions import ValidationError


def validate_required(data: Dict[str, Any], required_keys: List[str]) -> None:
    """Validates that all required keys are present in the configuration.

    Args:
        data: The configuration dictionary.
        required_keys: Keys that must be present.

    Raises:
        ValidationError: If any required key is missing.
    """
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValidationError(f"Missing required configuration keys: {', '.join(missing)}")


def validate_types(
    data: Dict[str, Any], expected_types: Dict[str, Union[type, Tuple[type, ...]]]
) -> None:
    """Validates that configuration values match expected Python types.

    Args:
        data: The configuration dictionary.
        expected_types: Dict mapping keys to expected types.

    Raises:
        ValidationError: If any value does not match expected types.
    """
    for key, expected_type in expected_types.items():
        if key in data:
            val = data[key]
            if not isinstance(val, expected_type):
                actual_name = type(val).__name__
                if isinstance(expected_type, tuple):
                    expected_name = f"one of ({', '.join(t.__name__ for t in expected_type)})"
                else:
                    expected_name = expected_type.__name__
                raise ValidationError(
                    f"Configuration key '{key}' must be of type {expected_name}, got {actual_name}"
                )


def validate_enum(data: Dict[str, Any], key: str, allowed_values: List[Any]) -> None:
    """Validates that a configuration key's value is in a set of allowed values.

    Args:
        data: The configuration dictionary.
        key: The key to check.
        allowed_values: List or tuple of permitted values.

    Raises:
        ValidationError: If the value is not allowed.
    """
    if key in data:
        val = data[key]
        if val not in allowed_values:
            raise ValidationError(
                f"Configuration key '{key}' value '{val}' is not one of: {allowed_values}"
            )


def validate_range(
    data: Dict[str, Any],
    key: str,
    min_value: Union[int, float, None] = None,
    max_value: Union[int, float, None] = None,
) -> None:
    """Validates that a configuration key's numeric value is within a range.

    Args:
        data: The configuration dictionary.
        key: The key to check.
        min_value: Optional minimum boundary (inclusive).
        max_value: Optional maximum boundary (inclusive).

    Raises:
        ValidationError: If value is not numeric or outside bounds.
    """
    if key in data:
        val = data[key]
        if not isinstance(val, (int, float)):
            raise ValidationError(
                f"Configuration key '{key}' must be numeric to validate range, got {type(val).__name__}"
            )
        if min_value is not None and val < min_value:
            raise ValidationError(
                f"Configuration key '{key}' value {val} must be >= {min_value}"
            )
        if max_value is not None and val > max_value:
            raise ValidationError(
                f"Configuration key '{key}' value {val} must be <= {max_value}"
            )


def validate_custom(
    data: Dict[str, Any],
    key: str,
    callback: Callable[[Any], bool],
    error_message: str | None = None,
) -> None:
    """Validates a configuration key's value using a custom callback.

    Args:
        data: The configuration dictionary.
        key: The key to check.
        callback: Function that takes the value and returns a boolean.
        error_message: Custom error message to show on validation failure.

    Raises:
        ValidationError: If the callback returns False or raises an error.
    """
    if key in data:
        val = data[key]
        try:
            success = callback(val)
        except Exception as e:
            raise ValidationError(
                f"Custom validation callback for '{key}' failed with error: {e}"
            ) from e

        if not success:
            msg = error_message or f"Custom validation failed for configuration key '{key}'"
            raise ValidationError(msg)
