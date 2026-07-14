"""Configuration settings container and strongly typed instantiation helpers."""

from dataclasses import fields, is_dataclass
from typing import Any, Dict, Type, TypeVar, Union, get_args, get_origin
from .exceptions import InvalidConfigurationError

T = TypeVar("T")


def _get_underlying_type(t: Any) -> Any:
    """Resolves the underlying type of Union or Optional types.

    Useful for identifying nested dataclasses wrapped in Optional.
    """
    origin = get_origin(t)
    if origin is Union:
        args = get_args(t)
        for arg in args:
            if arg is not type(None) and is_dataclass(arg):
                return arg
    return t


def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
    """Recursively instantiates a strongly typed dataclass from a dictionary.

    Args:
        cls: The target dataclass type.
        data: The configuration dictionary.

    Returns:
        An instance of the dataclass.

    Raises:
        TypeError: If cls is not a dataclass.
        InvalidConfigurationError: If instantiation fails due to missing or invalid fields.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} must be a dataclass.")

    kwargs = {}
    for f in fields(cls):
        if f.name in data:
            val = data[f.name]
            underlying = _get_underlying_type(f.type)
            if is_dataclass(underlying) and isinstance(val, dict):
                kwargs[f.name] = from_dict(underlying, val)
            else:
                kwargs[f.name] = val

    # Filter arguments to match initialized fields
    field_names = {f.name for f in fields(cls)}
    init_kwargs = {k: v for k, v in kwargs.items() if k in field_names}

    try:
        return cls(**init_kwargs)
    except TypeError as e:
        raise InvalidConfigurationError(
            f"Failed to initialize configuration dataclass '{cls.__name__}': {e}"
        ) from e
