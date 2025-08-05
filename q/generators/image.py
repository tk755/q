"""
Provider-agnostic image generation class.

Provides a clean, library-friendly interface for image generation that can be
used independently of the CLI while maintaining compatibility with all features.
"""

import base64
import string
import os
from typing import Optional, List, Dict, Any
from ..providers.base import LLMProvider
from ..providers.factory import get_default_provider
from ..config.manager import ConfigManager
from ..config.models import Message, MessageRole, ModelParameters, GenerationRequest, GenerationResponse
from ..utils.exceptions import GenerationError, ValidationError


class ImageGenerator:
    """
    Provider-agnostic image generation class.
    
    This class provides a clean interface for image generation that can be imported
    and used by other programs without any CLI dependencies. It supports various
    image sizes and quality settings.
    
    Example:
        generator = ImageGenerator()
        image_path = generator.generate_and_save("A serene mountain landscape")
        print(f"Image saved to: {image_path}")
    """
    
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        config: Optional[ConfigManager] = None
    ) -> None:
        """
        Initialize ImageGenerator with optional provider and configuration.
        
        Args:
            provider: LLM provider instance supporting image generation
            config: Configuration manager
            
        Raises:
            ConfigurationError: If API keys are not configured
            ProviderError: If provider doesn't support image generation
        """
        self.provider = provider or get_default_provider()
        self.config = config or ConfigManager()
        
        if not self.provider.supports_images:
            raise ValidationError(f"Provider {self.provider.provider_name} does not support image generation")
    
    def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "auto",
        style: Optional[str] = None
    ) -> bytes:
        """
        Generate image from text prompt.
        
        Args:
            prompt: Text description of desired image
            size: Image dimensions (256x256, 512x512, 1024x1024, 1792x1024, 1024x1792)
            quality: Image quality (auto, low, medium, high)
            style: Image style (vivid, natural)
        
        Returns:
            Image data as bytes (PNG format)
            
        Raises:
            GenerationError: If image generation fails
            ValidationError: If parameters are invalid
        """
        if not prompt.strip():
            raise ValidationError("Image prompt cannot be empty")
        
        if not self.validate_image_params(size, quality, style):
            raise ValidationError(f"Invalid image parameters: size={size}, quality={quality}, style={style}")
        
        # Create message for image generation
        messages = [
            Message(
                role=MessageRole.USER,
                content=f"Generate an image of the following: {prompt}."
            )
        ]
        
        # Create model parameters with image generation tools
        tools = [{
            'type': 'image_generation',
            'size': size,
            'quality': quality
        }]
        
        if style:
            tools[0]['style'] = style
        
        model_params = ModelParameters(
            model='gpt-4.1-mini',  # Use mini model for image generation
            max_output_tokens=1024,
            temperature=0.0,
            tools=tools
        )
        
        # Create generation request
        request = GenerationRequest(
            messages=messages,
            model_params=model_params,
            command_type="image"
        )
        
        try:
            # Generate image
            response = self.provider.generate_image(request)
            
            if not response.image_data:
                raise GenerationError("No image data received from provider")
            
            return response.image_data
            
        except (GenerationError, ValidationError):
            raise
        except Exception as e:
            raise GenerationError(f"Image generation failed: {e}")
    
    def generate_and_save(
        self,
        prompt: str,
        filename: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate image and save to file.
        
        Args:
            prompt: Text description of desired image
            filename: Output filename. If None, auto-generates based on prompt
            **kwargs: Same options as generate()
        
        Returns:
            Path to saved image file
            
        Raises:
            GenerationError: If generation fails
            OSError: If file cannot be saved
        """
        # Generate image
        image_data = self.generate(prompt, **kwargs)
        
        # Generate filename if not provided
        if filename is None:
            filename = self._generate_filename(prompt)
        
        # Save image
        return self.save_image(image_data, filename)
    
    def save_image(self, image_data: bytes, filename: str) -> str:
        """
        Save image data to file.
        
        Args:
            image_data: Raw image bytes
            filename: Output filename
        
        Returns:
            Full path to saved file
            
        Raises:
            OSError: If file cannot be saved
            ValidationError: If image data is invalid
        """
        if not image_data:
            raise ValidationError("Image data cannot be empty")
        
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Ensure filename has .png extension
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        try:
            # Get full path
            full_path = os.path.abspath(filename)
            
            # Write image data
            with open(full_path, 'wb') as f:
                f.write(image_data)
            
            return full_path
            
        except OSError as e:
            raise OSError(f"Failed to save image to {filename}: {e}")
    
    def _generate_filename(self, prompt: str) -> str:
        """
        Generate filename from prompt, matching original q.py behavior.
        
        Args:
            prompt: Image prompt text
            
        Returns:
            Generated filename
        """
        # Remove punctuation and replace spaces with underscores (from original q.py)
        clean_prompt = ''.join(c for c in prompt if c not in string.punctuation).replace(' ', '_')
        return f'q_{clean_prompt}.png'
    
    def validate_image_params(
        self,
        size: str,
        quality: str,
        style: Optional[str] = None
    ) -> bool:
        """
        Validate image generation parameters.
        
        Args:
            size: Image size
            quality: Image quality
            style: Image style (optional)
            
        Returns:
            True if parameters are valid
        """
        valid_sizes = ['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792']
        valid_qualities = ['auto', 'low', 'medium', 'high']
        valid_styles = ['vivid', 'natural', None]
        
        return (
            size in valid_sizes and
            quality in valid_qualities and
            style in valid_styles
        )
    
    def get_supported_sizes(self) -> List[str]:
        """Get list of supported image sizes."""
        return ['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792']
    
    def estimate_cost(self, size: str, quality: str) -> float:
        """
        Estimate generation cost in USD.
        
        Args:
            size: Image size
            quality: Image quality
            
        Returns:
            Estimated cost in USD
        """
        # Rough estimates based on OpenAI pricing (as of 2024)
        base_costs = {
            '256x256': 0.016,
            '512x512': 0.018,
            '1024x1024': 0.020,
            '1792x1024': 0.040,
            '1024x1792': 0.040
        }
        
        quality_multipliers = {
            'auto': 1.0,
            'low': 0.8,
            'medium': 1.0,
            'high': 1.2
        }
        
        base_cost = base_costs.get(size, 0.020)
        multiplier = quality_multipliers.get(quality, 1.0)
        
        return base_cost * multiplier