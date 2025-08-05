"""
Explain command implementation.

Handles the -e/--explain command for explaining code, commands, or technical concepts.
"""

from typing import List
from .base import BaseCommand
from ..config.models import Message, MessageRole, ModelParameters


class ExplainCommand(BaseCommand):
    """
    Command for explaining code, commands, or technical concepts.
    
    Maintains exact behavior from original q.py explain command with
    focused prompting for concise technical explanations.
    """
    
    @property
    def flags(self) -> List[str]:
        """Command flags."""
        return ['-e', '--explain']
    
    @property
    def description(self) -> str:
        """Description for help text."""
        return "explain code, commands, or a technical concept"
    
    def get_messages(self, text: str) -> List[Message]:
        """
        Get messages for explain command.
        
        Uses the exact system prompt from original q.py to maintain
        consistent explanation behavior.
        
        Args:
            text: Code, command, or concept to explain
            
        Returns:
            List of messages for explanation request
        """
        return [
            Message(
                role=MessageRole.DEVELOPER,
                content=(
                    "You are a programming assistant. Given a shell command, code snippet, or technical concept, "
                    "provide a concise and technical explanation. Assume the reader is an experienced developer. "
                    "Avoid restating the code or command. Avoid explaining obvious syntax. "
                    "Avoid breaking the answer into bullet points unless necessary. "
                    "The response should be a single short paragraph optimized for clarity."
                )
            ),
            Message(
                role=MessageRole.USER,
                content=f"Explain: {text}"
            )
        ]
    
    def get_model_params(self) -> ModelParameters:
        """
        Get model parameters for explain command.
        
        Uses the mini model for cost efficiency as explanations
        don't require the most powerful model.
        
        Returns:
            Model parameters optimized for explanations
        """
        return ModelParameters(
            model='gpt-4.1-mini',
            max_output_tokens=1024,
            temperature=0.0
        )