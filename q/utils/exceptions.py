"""
Exception hierarchy for the Q library.

Provides structured error handling with context information for better
debugging and user experience.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ErrorContext:
    """Context information for errors to aid in debugging."""
    operation: str
    provider: Optional[str] = None
    model: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None


class QError(Exception):
    """Base exception for Q library."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context


class ConfigurationError(QError):
    """Configuration-related errors (missing API keys, invalid settings, etc)."""
    pass


class ProviderError(QError):
    """Provider-related errors (API failures, connection issues, etc)."""
    pass


class ProviderNotFoundError(ProviderError):
    """Provider not found or not available."""
    pass


class GenerationError(QError):
    """Text/image generation errors (model failures, invalid responses, etc)."""
    pass


class ValidationError(QError):
    """Input validation errors (invalid parameters, malformed input, etc)."""
    pass


class AuthenticationError(ProviderError):
    """API authentication errors (invalid keys, expired tokens, etc)."""
    pass


class RateLimitError(ProviderError):
    """API rate limit exceeded."""
    pass


class InsufficientCreditsError(ProviderError):
    """Insufficient API credits or quota exceeded."""
    pass