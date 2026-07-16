"""Exceptions for the providers package.

Hierarchy
---------
ProviderError
├── ProviderNotFoundError
├── ProviderRegistrationError
├── ProviderConfigurationError
└── UnsupportedModelError
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base exception for all provider-layer errors.

    All public exceptions in this package inherit from this class, allowing
    callers to catch the entire family with a single ``except ProviderError``.

    Attributes:
        provider_name: The name of the provider that raised this error, or
            ``None`` when the context is unknown.
    """

    def __init__(self, message: str, *, provider_name: str | None = None) -> None:
        """Initializes ProviderError.

        Args:
            message: Human-readable description of the error.
            provider_name: Optional name of the offending provider.
        """
        super().__init__(message)
        self.provider_name = provider_name


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not registered.

    Example::

        raise ProviderNotFoundError(
            "No provider registered under 'openai'.",
            provider_name="openai",
        )
    """


class ProviderRegistrationError(ProviderError):
    """Raised when a provider registration attempt fails.

    Common causes include duplicate names and non-conforming implementations.

    Attributes:
        provider_name: The name that was being registered.
    """


class ProviderConfigurationError(ProviderError):
    """Raised when a provider is misconfigured.

    Use this when required credentials, endpoints, or options are missing or
    logically invalid *at configuration time*, not at request time.

    Attributes:
        provider_name: The name of the misconfigured provider.
        config_key: The specific configuration field that is invalid, or
            ``None`` when the error is holistic.
    """

    def __init__(
        self,
        message: str,
        *,
        provider_name: str | None = None,
        config_key: str | None = None,
    ) -> None:
        """Initializes ProviderConfigurationError.

        Args:
            message: Human-readable description of the misconfiguration.
            provider_name: Optional name of the offending provider.
            config_key: Optional name of the specific invalid config field.
        """
        super().__init__(message, provider_name=provider_name)
        self.config_key = config_key


class UnsupportedModelError(ProviderError):
    """Raised when a provider does not support the requested model.

    Attributes:
        provider_name: The provider that received the request.
        model_id: The unsupported model identifier that was requested.
    """

    def __init__(
        self,
        message: str,
        *,
        provider_name: str | None = None,
        model_id: str | None = None,
    ) -> None:
        """Initializes UnsupportedModelError.

        Args:
            message: Human-readable description of the error.
            provider_name: Optional name of the queried provider.
            model_id: The model identifier that is not supported.
        """
        super().__init__(message, provider_name=provider_name)
        self.model_id = model_id
