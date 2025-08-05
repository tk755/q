"""
Abstract base class for LLM providers.

Defines the interface that all LLM providers must implement to ensure
consistent behavior across different service providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..config.models import GenerationRequest, GenerationResponse


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers must implement this interface to ensure consistent
    behavior and easy swapping between different service providers.
    """
    
    @abstractmethod
    def generate_text(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate text response from request.
        
        Args:
            request: Generation request with messages and parameters
            
        Returns:
            Generation response with text and metadata
            
        Raises:
            GenerationError: If text generation fails
            AuthenticationError: If API authentication fails
            RateLimitError: If rate limit is exceeded
        """
        pass
    
    @abstractmethod
    def generate_image(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate image response from request.
        
        Args:
            request: Generation request with prompt and parameters
            
        Returns:
            Generation response with image data and metadata
            
        Raises:
            GenerationError: If image generation fails
            AuthenticationError: If API authentication fails
            RateLimitError: If rate limit is exceeded
            ValidationError: If provider doesn't support image generation
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Test if provider connection is working.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models from this provider.
        
        Returns:
            List of model names/identifiers
        """
        pass
    
    @property
    @abstractmethod
    def supports_images(self) -> bool:
        """
        Whether provider supports image generation.
        
        Returns:
            True if image generation is supported
        """
        pass
    
    @property
    @abstractmethod
    def supports_web_search(self) -> bool:
        """
        Whether provider supports web search capabilities.
        
        Returns:
            True if web search is supported
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Name of the provider for identification.
        
        Returns:
            Provider name (e.g., "openai", "anthropic")
        """
        pass