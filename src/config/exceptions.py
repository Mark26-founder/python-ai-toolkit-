"""Exceptions for the config package."""


class ConfigError(Exception):
    """Base exception for all configuration-related errors."""
    pass


class MissingConfigurationError(ConfigError):
    """Raised when a required configuration key or file is missing."""
    pass


class InvalidConfigurationError(ConfigError):
    """Raised when configuration values are malformed or invalid."""
    pass


class ConfigurationSourceError(ConfigError):
    """Raised when loading from a configuration source fails."""
    pass


class ValidationError(ConfigError):
    """Raised when configuration validation fails."""
    pass
