"""
Image generation command implementation.

Handles the -i/--image command for generating images.
"""

from typing import List
from .base import BaseCommand
from ..config.models import Message, MessageRole, ModelParameters


class ImageCommand(BaseCommand):
    """
    Command for generating images.
    
    Maintains exact behavior from original q.py image command with
    image generation tools configuration.
    """
    
    @property
    def flags(self) -> List[str]:
        """Command flags."""
        return ['-i', '--image']
    
    @property
    def description(self) -> str:
        """Description for help text."""
        return "generate an image (very expensive)"
    
    def get_messages(self, text: str) -> List[Message]:
        """
        Get messages for image generation.
        
        Uses simple prompting as the actual image generation
        is handled by the tools configuration.
        
        Args:
            text: Description of desired image
            
        Returns:
            List of messages for image generation request
        """
        return [
            Message(
                role=MessageRole.USER,
                content=f"Generate an image of the following: {text}."
            )
        ]
    
    def get_model_params(self) -> ModelParameters:
        """
        Get model parameters for image generation.
        
        Uses mini model with image generation tools configured
        exactly as in original q.py.
        
        Returns:
            Model parameters with image generation tools
        """
        return ModelParameters(
            model='gpt-4.1-mini',
            max_output_tokens=1024,
            temperature=0.0,
            tools=[{
                'type': 'image_generation',
                'size': '1024x1024',
                'quality': 'auto'  # low, medium, high
            }]
        )