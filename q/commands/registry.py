"""
Command registration and discovery system.

Manages the registry of available commands and provides lookup functionality
for the CLI and library usage.
"""

from typing import Dict, List, Optional, Type
from .base import BaseCommand
from ..utils.exceptions import ValidationError


# Registry of commands by flag
_commands: Dict[str, BaseCommand] = {}
_command_classes: Dict[str, Type[BaseCommand]] = {}


def register_command(command_class: Type[BaseCommand]) -> None:
    """
    Register a new command class.
    
    Args:
        command_class: Command class that implements BaseCommand interface
        
    Raises:
        ValidationError: If command class is invalid or flags conflict
    """
    if not issubclass(command_class, BaseCommand):
        raise ValidationError(f"Command class {command_class.__name__} must implement BaseCommand interface")
    
    try:
        instance = command_class()
    except Exception as e:
        raise ValidationError(f"Failed to instantiate command class {command_class.__name__}: {e}")
    
    # Check for flag conflicts
    for flag in instance.flags:
        if flag in _commands:
            existing_command = _commands[flag]
            raise ValidationError(
                f"Flag '{flag}' is already registered to {existing_command.__class__.__name__}"
            )
    
    # Register the command for all its flags
    if instance.flags:
        for flag in instance.flags:
            _commands[flag] = instance
    else:
        # Special handling for default command (empty flags)
        _commands[''] = instance
    
    # Store the class for reference
    _command_classes[command_class.__name__] = command_class


def get_command(flag: str) -> Optional[BaseCommand]:
    """
    Get command instance by flag.
    
    Args:
        flag: Command flag (e.g., '-c', '--code')
        
    Returns:
        Command instance or None if not found
    """
    return _commands.get(flag)


def get_default_command() -> Optional[BaseCommand]:
    """
    Get the default command (command with empty flags list).
    
    Returns:
        Default command instance or None if not found
    """
    return _commands.get('')


def list_commands() -> List[BaseCommand]:
    """
    List all registered commands.
    
    Returns:
        List of unique command instances
    """
    seen = set()
    unique_commands = []
    
    for command in _commands.values():
        if id(command) not in seen:
            seen.add(id(command))
            unique_commands.append(command)
    
    return unique_commands


def get_all_flags() -> List[str]:
    """
    Get all registered command flags.
    
    Returns:
        List of all command flags
    """
    return list(_commands.keys())


def validate_commands() -> List[str]:
    """
    Validate command registry for consistency.
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check if there is a default command
    default_command = get_default_command()
    if default_command is None:
        errors.append("No default command found")
    
    # Check for multiple default commands (should not happen with new registration logic)
    default_commands = [cmd for cmd in list_commands() if not cmd.flags]
    if len(default_commands) > 1:
        errors.append("More than one default command found")
    
    # Check for duplicate flags (should not happen due to registration validation)
    all_flags = get_all_flags()
    duplicates = set(flag for flag in all_flags if all_flags.count(flag) > 1)
    if duplicates:
        errors.append(f"Duplicate command flags found: {', '.join(duplicates)}")
    
    return errors