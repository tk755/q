"""
Code generation command implementation.

Handles the -c/--code command for generating code snippets.
"""

from typing import List
from .base import BaseCommand
from ..config.models import Message, MessageRole, ModelParameters


# Constants from original q.py
DEFAULT_CODE = 'python'


class CodeCommand(BaseCommand):
    """
    Command for generating code snippets.
    
    Maintains exact behavior from original q.py code command with
    focused prompting for clean, idiomatic code generation.
    """
    
    @property
    def flags(self) -> List[str]:
        """Command flags."""
        return ['-c', '--code']
    
    @property
    def description(self) -> str:
        """Description for help text."""
        return f"generate a code snippet (default: {DEFAULT_CODE})"
    
    @property
    def clip_output(self) -> bool:
        """Code command copies output to clipboard by default."""
        return True
    
    def get_messages(self, text: str) -> List[Message]:
        """
        Get messages for code generation command.
        
        Uses the exact system prompt from original q.py to maintain
        consistent code generation behavior.
        
        Args:
            text: Description of desired code functionality
            
        Returns:
            List of messages for code generation request
        """
        return [
            Message(
                role=MessageRole.DEVELOPER,
                content=(
                    f"You are a coding assistant. Given a natural language description, generate a code snippet "
                    f"that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. "
                    f"Respond with only the code snippet, without explanations, additional text, or formatting. "
                    f"Assume the programming language is {DEFAULT_CODE} unless otherwise specified."
                )
            ),
            Message(
                role=MessageRole.USER,
                content=(
                    f"Generate a code snippet to accomplish the following task: {text}. "
                    f"Respond only with the code, without explanation or additional text."
                )
            )
        ]
    
    def get_model_params(self) -> ModelParameters:
        """
        Get model parameters for code generation.
        
        Uses the full model for better code quality and reasoning.
        
        Returns:
            Model parameters optimized for code generation
        """
        return ModelParameters(
            model='gpt-4.1',  # Full model for better code quality
            max_output_tokens=1024,
            temperature=0.0
        )