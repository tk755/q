"""
Default command implementation.

Handles the default conversation mode when no specific command flag is provided.
This maintains backward compatibility with the original q.py default behavior.
"""

from typing import List
from .base import BaseCommand
from ..config.models import Message, MessageRole, ModelParameters
from ..config.manager import get_default_config


class DefaultCommand(BaseCommand):
    """
    Default command for general conversation.
    
    This command is used when no specific flag is provided and handles
    follow-up conversations using stored message history.
    """
    
    @property
    def flags(self) -> List[str]:
        """Default command has no flags."""
        return []
    
    @property
    def description(self) -> str:
        """Description for help text."""
        return "follow-up on the previous response"
    
    @property
    def clip_output(self) -> bool:
        """Use stored clip_output setting."""
        config = get_default_config()
        return config._load_resource('clip_output', False)
    
    def get_messages(self, text: str) -> List[Message]:
        """
        Get messages for default command, including conversation history.
        
        This maintains the exact behavior of the original q.py default command
        which loads previous messages and appends the new user message.
        
        Args:
            text: User input text
            
        Returns:
            List of messages including history
        """
        config = get_default_config()
        
        # Load conversation history
        stored_messages = config._load_resource('messages', [])
        
        # Convert stored messages to Message objects
        messages = []
        for msg_data in stored_messages:
            if isinstance(msg_data, dict):
                if 'role' in msg_data and 'content' in msg_data:
                    try:
                        role = MessageRole(msg_data['role'])
                        messages.append(Message(role=role, content=msg_data['content']))
                    except (ValueError, KeyError):
                        # Handle legacy format - preserve as-is for compatibility
                        messages.append(msg_data)
                else:
                    # Handle legacy format (image generation calls, etc.)
                    messages.append(msg_data)
        
        # Add new user message
        messages.append(Message(role=MessageRole.USER, content=text))
        
        return messages
    
    def get_model_params(self) -> ModelParameters:
        """
        Get model parameters, using stored values from previous commands.
        
        Returns:
            Model parameters from configuration or defaults
        """
        config = get_default_config()
        
        # Load stored model args from previous command
        stored_args = config._load_resource('model_args', {})
        
        # Default parameters from original q.py
        defaults = {
            'model': 'gpt-4.1-mini',
            'max_output_tokens': 1024,
            'temperature': 0.0
        }
        
        # Merge with stored args
        merged = {**defaults, **stored_args}
        
        return ModelParameters(
            model=merged['model'],
            max_output_tokens=merged['max_output_tokens'],
            temperature=merged['temperature'],
            tools=merged.get('tools')
        )