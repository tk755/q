"""
Command system for the Q library.

Provides an extensible command system that maintains backward compatibility
with the original q.py command structure while enabling new command additions.
"""

from .base import BaseCommand
from .registry import register_command, get_command, list_commands, get_default_command, validate_commands
from .explain import ExplainCommand
from .code import CodeCommand
from .shell import ShellCommand
from .image import ImageCommand
from .web import WebCommand
from .default import DefaultCommand

# Auto-register all built-in commands
register_command(DefaultCommand)
register_command(ExplainCommand)
register_command(CodeCommand)
register_command(ShellCommand)
register_command(ImageCommand)
register_command(WebCommand)

__all__ = [
    "BaseCommand",
    "register_command",
    "get_command", 
    "list_commands",
    "get_default_command",
    "validate_commands",
    "ExplainCommand",
    "CodeCommand",
    "ShellCommand", 
    "ImageCommand",
    "WebCommand",
    "DefaultCommand"
]