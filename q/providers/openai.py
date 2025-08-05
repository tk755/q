"""
OpenAI provider implementation.

Implements the LLMProvider interface for OpenAI's API, maintaining exact
compatibility with the original q.py implementation.
"""

import base64
import getpass
import sys
from typing import List, Dict, Any, Optional, Tuple
import openai
from termcolor import cprint

from .base import LLMProvider
from ..config.models import GenerationRequest, GenerationResponse, Message
from ..utils.exceptions import (
    GenerationError, 
    AuthenticationError, 
    RateLimitError, 
    ProviderError,
    ValidationError
)


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider implementation with backward compatibility.
    
    Maintains the exact behavior of the original q.py OpenAI integration
    including API key management and response processing.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from config or prompt user.
        """
        self._api_key = api_key
        self._client: Optional[openai.OpenAI] = None
    
    def _get_client(self) -> openai.OpenAI:
        """
        Get OpenAI client, maintaining exact same behavior as original q.py get_client().
        
        Returns:
            Configured OpenAI client
            
        Raises:
            AuthenticationError: If API key is invalid
        """
        if self._client is not None:
            return self._client
        
        api_key = self._api_key
        
        # Import here to avoid circular imports
        from ..config.manager import get_default_config
        config = get_default_config()
        
        if api_key is None:
            api_key = config._load_resource('openai_key', None)
        
        if api_key is None:
            cprint(f'Error: OpenAI API key not found. Please paste your API key: ', 'red', end='', flush=True, file=sys.stderr)
            api_key = getpass.getpass(prompt='')
            config._save_resource('openai_key', api_key)

        while True:
            try:
                client = openai.OpenAI(api_key=api_key)
                client.models.list()  # test the API key
                self._client = client
                return client
            
            except openai.APIError:
                cprint(f'Error: OpenAI API key not valid. Please paste your API key: ', 'red', end='', flush=True, file=sys.stderr)
                api_key = getpass.getpass(prompt='')
                config._save_resource('openai_key', api_key)
    
    def _prompt_model(self, model_args: Dict[str, Any], messages: List[Dict[str, str]]) -> Tuple[str, Any]:
        """
        Prompt the model, maintaining exact same behavior as original q.py prompt_model().
        
        Args:
            model_args: Model arguments
            messages: List of message dictionaries
            
        Returns:
            Tuple of (text_response, image_response)
        """
        try:
            response = self._get_client().responses.create(
                input=messages,
                **model_args
            )

            # extract and process text response - done by caller
            text_response = response.output_text

            # extract image response
            image_response = None
            for output in response.output:
                if output.type == 'image_generation_call':
                    image_response = output
                    break

            return text_response, image_response
            
        except openai.APIError as e:
            if "authentication" in str(e).lower():
                raise AuthenticationError(f"OpenAI API authentication failed: {e}")
            elif "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                raise RateLimitError(f"OpenAI API rate limit exceeded: {e}")
            else:
                raise GenerationError(f"OpenAI API error: {e}")
        except Exception as e:
            raise GenerationError(f"Unexpected error during generation: {e}")
    
    def generate_text(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate text response using OpenAI API.
        
        Args:
            request: Generation request
            
        Returns:
            Generation response with text
        """
        # Convert messages to dict format for API
        message_dicts = []
        for msg in request.messages:
            if hasattr(msg, 'to_dict'):
                message_dicts.append(msg.to_dict())
            else:
                message_dicts.append(msg)
        
        # Convert model parameters to dict
        model_args = request.model_params.to_dict()
        
        try:
            text_response, image_response = self._prompt_model(model_args, message_dicts)
            
            return GenerationResponse(
                text=text_response,
                image_data=None,
                model_used=model_args.get('model'),
                usage_stats=None,  # Could be extracted from OpenAI response if needed
                raw_response=None
            )
        except (AuthenticationError, RateLimitError, GenerationError):
            raise
        except Exception as e:
            raise GenerationError(f"Text generation failed: {e}")
    
    def generate_image(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate image response using OpenAI API.
        
        Args:
            request: Generation request with image parameters
            
        Returns:
            Generation response with image data
        """
        # Convert messages to dict format for API
        message_dicts = []
        for msg in request.messages:
            if hasattr(msg, 'to_dict'):
                message_dicts.append(msg.to_dict())
            else:
                message_dicts.append(msg)
        
        # Convert model parameters to dict
        model_args = request.model_params.to_dict()
        
        # Ensure image generation tools are present
        if not model_args.get('tools') or not any(
            tool.get('type') == 'image_generation' for tool in model_args.get('tools', [])
        ):
            raise ValidationError("Image generation requires image_generation tool in model parameters")
        
        try:
            text_response, image_response = self._prompt_model(model_args, message_dicts)
            
            image_data = None
            if image_response:
                # Extract image data from response
                image_data = base64.b64decode(image_response.result)
            
            return GenerationResponse(
                text=text_response,
                image_data=image_data,
                model_used=model_args.get('model'),
                usage_stats=None,
                raw_response=image_response
            )
        except (AuthenticationError, RateLimitError, GenerationError, ValidationError):
            raise
        except Exception as e:
            raise GenerationError(f"Image generation failed: {e}")
    
    def validate_connection(self) -> bool:
        """
        Test if OpenAI connection is working.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            self._get_client().models.list()
            return True
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available OpenAI models.
        
        Returns:
            List of model names
        """
        try:
            models = self._get_client().models.list()
            return [model.id for model in models.data]
        except Exception:
            # Return common OpenAI models as fallback
            return [
                "gpt-4.1",
                "gpt-4.1-mini", 
                "gpt-4",
                "gpt-4-turbo",
                "gpt-3.5-turbo"
            ]
    
    @property
    def supports_images(self) -> bool:
        """OpenAI supports image generation."""
        return True
    
    @property
    def supports_web_search(self) -> bool:
        """OpenAI supports web search through tools."""
        return True
    
    @property
    def provider_name(self) -> str:
        """Provider name for identification."""
        return "openai"