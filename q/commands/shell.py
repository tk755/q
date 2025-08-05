"""
Shell command generation implementation.

Handles the -s/--shell command for generating shell commands.
"""

from typing import List
from .base import BaseCommand
from ..config.models import Message, MessageRole, ModelParameters


# Constants from original q.py
DEFAULT_SHELL = 'debian+bash'


class ShellCommand(BaseCommand):
    """
    Command for generating shell commands.
    
    Maintains exact behavior from original q.py shell command with
    focused prompting for safe, minimal shell commands.
    """
    
    @property
    def flags(self) -> List[str]:
        """Command flags."""
        return ['-s', '--shell']
    
    @property
    def description(self) -> str:
        """Description for help text."""
        return f"generate a shell command (default: {DEFAULT_SHELL})"
    
    @property
    def clip_output(self) -> bool:
        """Shell command copies output to clipboard by default."""
        return True
    
    def get_messages(self, text: str) -> List[Message]:
        """
        Get messages for shell command generation.
        
        Uses the exact system prompt from original q.py to maintain
        consistent shell command generation behavior with safety considerations.
        
        Args:
            text: Description of desired shell operation
            
        Returns:
            List of messages for shell command generation request
        """
        return [
            Message(
                role=MessageRole.DEVELOPER,
                content=(
                    f"You are a command-line assistant. Given a natural language task description, "
                    f"generate the simplest single shell command that accomplishes the task. "
                    f"Favor minimal, commonly available commands with no extra formatting or piping. "
                    f"Avoid commands that could delete, overwrite, or modify important files or system settings "
                    f"(e.g., rm -rf, dd, mkfs, chmod -R, chown, kill -9). "
                    f"Respond with only the command, without explanations, additional text, or formatting. "
                    f"Assume a {DEFAULT_SHELL} shell unless otherwise specified."
                )
            ),
            Message(
                role=MessageRole.USER,
                content=(
                    f"Generate a single shell command to accomplish the following task: {text}. "
                    f"Respond with only the command, without explanation or additional text."
                )
            )
        ]
    
    def get_model_params(self) -> ModelParameters:
        """
        Get model parameters for shell command generation.
        
        Uses the default model parameters from original q.py.
        
        Returns:
            Model parameters for shell command generation
        """
        return ModelParameters(
            model='gpt-4.1-mini',
            max_output_tokens=1024,
            temperature=0.0
        )