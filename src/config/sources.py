"""Configuration sources implementation representing different inputs."""

import json
import os
from typing import Any, Dict, Protocol
from .exceptions import ConfigurationSourceError

try:
    import tomllib
except ImportError:
    # Fallback to tomllib since Python 3.11+ is standard.
    # In older versions, we import tomllib-compatible library.
    import tomllib  # type: ignore


class ConfigSource(Protocol):
    """Protocol defining the interface for a configuration source."""

    def load(self) -> Dict[str, Any]:
        """Loads configuration data from the source.

        Returns:
            A dictionary of configuration keys and values.

        Raises:
            ConfigurationSourceError: If the source fails to load.
        """
        ...


class DictSource:
    """Loads configuration from an in-memory dictionary."""

    def __init__(self, data: Dict[str, Any]) -> None:
        """Initializes the dictionary source.

        Args:
            data: The source configuration dictionary.
        """
        self._data = data

    def load(self) -> Dict[str, Any]:
        """Returns a copy of the wrapped dictionary."""
        return dict(self._data)


class EnvSource:
    """Loads configuration from environment variables."""

    def __init__(self, prefix: str = "", strip_prefix: bool = True) -> None:
        """Initializes the environment source.

        Args:
            prefix: Filter variables starting with this prefix.
            strip_prefix: Whether to remove the prefix from the returned keys.
        """
        self.prefix = prefix
        self.strip_prefix = strip_prefix

    def load(self) -> Dict[str, Any]:
        """Loads and filters environment variables."""
        result = {}
        for key, val in os.environ.items():
            if key.startswith(self.prefix):
                target_key = key[len(self.prefix) :] if self.strip_prefix else key
                result[target_key] = val
        return result


class JsonSource:
    """Loads configuration from a JSON file."""

    def __init__(self, filepath: str, ignore_missing: bool = False) -> None:
        """Initializes the JSON source.

        Args:
            filepath: Path to the JSON configuration file.
            ignore_missing: If True, returns empty dict if file does not exist.
        """
        self.filepath = filepath
        self.ignore_missing = ignore_missing

    def load(self) -> Dict[str, Any]:
        """Reads and parses JSON file contents."""
        if not os.path.exists(self.filepath):
            if self.ignore_missing:
                return {}
            raise ConfigurationSourceError(
                f"JSON configuration file not found: {self.filepath}"
            )
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ConfigurationSourceError("JSON configuration must be a dictionary.")
                return data
        except Exception as e:
            raise ConfigurationSourceError(f"Failed to load JSON configuration: {e}") from e


class TomlSource:
    """Loads configuration from a TOML file."""

    def __init__(self, filepath: str, ignore_missing: bool = False) -> None:
        """Initializes the TOML source.

        Args:
            filepath: Path to the TOML configuration file.
            ignore_missing: If True, returns empty dict if file does not exist.
        """
        self.filepath = filepath
        self.ignore_missing = ignore_missing

    def load(self) -> Dict[str, Any]:
        """Reads and parses TOML file contents."""
        if not os.path.exists(self.filepath):
            if self.ignore_missing:
                return {}
            raise ConfigurationSourceError(
                f"TOML configuration file not found: {self.filepath}"
            )
        try:
            with open(self.filepath, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ConfigurationSourceError(f"Failed to load TOML configuration: {e}") from e
