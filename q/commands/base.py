"""
Abstract base class for commands.

Defines the interface that all commands must implement to ensure
consistent behavior and easy extensibility.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..config.models import Message, ModelParameters


class BaseCommand(ABC):
    """
    Abstract base class for commands.
    
    All commands must implement this interface to ensure consistent
    behavior and integration with the command system.
    """
    
    @abstractmethod
    def get_messages(self, text: str) -> List[Message]:
        """
        Get message list for this command.
        
        Args:
            text: User input text
            
        Returns:
            List of messages to send to the LLM
        """
        pass
    
    @abstractmethod
    def get_model_params(self) -> ModelParameters:
        """
        Get model parameters for this command.
        
        Returns:
            Model parameters including model name, temperature, etc.
        """
        pass
    
    @property
    @abstractmethod 
    def flags(self) -> List[str]:
        """
        Command flags (e.g., ['-c', '--code']).
        
        Returns:
            List of command flags that trigger this command
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Command description for help text.
        
        Returns:
            Human-readable description of the command
        """
        pass
    
    @property
    def clip_output(self) -> bool:
        """
        Whether to copy output to clipboard by default.
        
        Returns:
            True if output should be copied to clipboard
        """
        return False
    
    def validate_input(self, text: str) -> bool:
        """
        Validate command input.
        
        Args:
            text: User input text
            
        Returns:
            True if input is valid, False otherwise
        """
        return len(text.strip()) > 0
    
    def process_response(self, response: str) -> str:
        """
        Post-process command response.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Processed response
        """
        return response
    
    def get_command_config(self) -> Dict[str, Any]:
        """
        Get command configuration in original q.py format for backward compatibility.
        
        Returns:
            Dictionary matching original COMMANDS list format
        """
        messages = self.get_messages("{text}")  # Placeholder will be replaced
        model_params = self.get_model_params()
        
        # Convert messages to dict format
        message_dicts = []
        for msg in messages:
            if hasattr(msg, 'to_dict'):
                message_dicts.append(msg.to_dict())
            else:
                message_dicts.append(msg)
        
        return {
            'flags': self.flags,
            'description': self.description,
            'clip_output': self.clip_output,
            'model_args': model_params.to_dict(),
            'messages': message_dicts
        }