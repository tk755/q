"""
Provider factory for creating and managing LLM providers.

Provides a centralized way to create provider instances and supports
registration of new providers for extensibility.
"""

from typing import Dict, List, Optional, Type, Any
from .base import LLMProvider
from .openai import OpenAIProvider
from ..config.manager import ConfigManager
from ..utils.exceptions import ProviderNotFoundError, ConfigurationError


# Registry of available providers
_PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "openai": OpenAIProvider,
}


def register_provider(name: str, provider_class: Type[LLMProvider]) -> None:
    """
    Register a new provider class.
    
    Args:
        name: Provider name (e.g., "anthropic", "huggingface")
        provider_class: Provider class that implements LLMProvider interface
        
    Raises:
        ValidationError: If provider_class doesn't implement LLMProvider
    """
    if not issubclass(provider_class, LLMProvider):
        raise ConfigurationError(f"Provider class {provider_class.__name__} must implement LLMProvider interface")
    
    _PROVIDERS[name] = provider_class


def list_providers() -> List[str]:
    """
    List all available provider names.
    
    Returns:
        List of registered provider names
    """
    return list(_PROVIDERS.keys())


def get_provider(
    provider_name: str = "openai",
    config: Optional[ConfigManager] = None,
    **kwargs
) -> LLMProvider:
    """
    Get provider instance by name.
    
    Args:
        provider_name: Name of provider (openai, anthropic, etc.)
        config: Configuration manager instance
        **kwargs: Provider-specific configuration options
        
    Returns:
        Configured provider instance
        
    Raises:
        ProviderNotFoundError: If provider is not available
        ConfigurationError: If provider configuration is invalid
    """
    if provider_name not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ProviderNotFoundError(
            f"Provider '{provider_name}' not found. Available providers: {available}"
        )
    
    provider_class = _PROVIDERS[provider_name]
    
    # Get configuration if not provided
    if config is None:
        config = ConfigManager()
    
    try:
        # Handle provider-specific initialization
        if provider_name == "openai":
            api_key = kwargs.get('api_key') or config.get_api_key('openai')
            return provider_class(api_key=api_key)
        else:
            # Generic initialization for other providers
            return provider_class(**kwargs)
            
    except Exception as e:
        raise ConfigurationError(f"Failed to initialize {provider_name} provider: {e}")


def get_default_provider(config: Optional[ConfigManager] = None) -> LLMProvider:
    """
    Get the default provider instance.
    
    Args:
        config: Configuration manager instance
        
    Returns:
        Default provider instance (currently OpenAI)
    """
    return get_provider("openai", config)