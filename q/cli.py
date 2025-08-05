"""
CLI entry point for the Q library.

Maintains 100% backward compatibility with the original q.py script while
using the new modular architecture internally.
"""

import base64
import os
import string
import sys
from typing import Any, Dict, List, Tuple

import pyperclip
from colorama import just_fix_windows_console
from termcolor import colored, cprint

from .commands.registry import get_command, get_default_command, list_commands, validate_commands
from .config.manager import get_default_config
from .generators.text import TextGenerator
from .generators.image import ImageGenerator
from .providers.factory import get_default_provider
from .utils.processing import ResponseProcessor
from .utils.exceptions import QError

# Module metadata - maintain exact values from original q.py
__version__ = '1.4.0'
DESCRIPTION = 'An LLM-powered programming copilot from the comfort of your command line'

# Options from original q.py
OPTIONS = [
    {
        'name': 'overwrite',
        'flags': ['-o', '--overwrite'],
        'description': 'overwrite the previous command',
    },
    {
        'name': 'no-clip',
        'flags': ['-n', '--no-clip'],
        'description': 'do not copy the output to the clipboard',
    },
    { 
        'name': 'verbose',
        'flags': ['-v', '--verbose'],
        'description': 'print the model parameters and message history',
    },
]


def run_command(cmd_config: Dict, text: str, **opt_args):
    """
    Run command with exact same behavior as original q.py run_command function.
    
    Args:
        cmd_config: Command configuration dictionary
        text: Input text
        **opt_args: Option arguments (overwrite, no-clip, verbose)
    """
    config = get_default_config()
    
    # Load model and messages from command - exact same logic as original
    from .config.models import ModelParameters
    
    # Default model args from original q.py
    DEFAULT_MODEL_ARGS = {
        'model': 'gpt-4.1-mini',
        'max_output_tokens': 1024,
        'temperature': 0.0
    }
    
    model_args = {**DEFAULT_MODEL_ARGS, **cmd_config.get('model_args', {})}
    messages = [
        {role: content.replace('{text}', text) for role, content in msg.items()} 
        for msg in cmd_config.get('messages', [])
    ]

    # Save model args for follow-up commands
    config._save_resource('model_args', model_args)
    # Save command args for follow-up commands
    config._save_resource('clip_output', cmd_config.get('clip_output', False))

    # Overwrite previous follow-up command - exact same logic as original
    if opt_args.get('overwrite', False):
        # Remove messages from second-to-last user message to last user message
        user_msg_indices = [i for i, msg in enumerate(messages) if msg.get('role') == 'user']
        if len(user_msg_indices) > 1:
            messages = messages[:user_msg_indices[-2]] + messages[user_msg_indices[-1]:]
        else:
            cprint(f'Error: No previous command to overwrite.', 'red', file=sys.stderr)
            sys.exit(1)

    # Use the modular system to generate response
    try:
        provider = get_default_provider()
        
        # Check if this is an image generation command
        is_image_command = any(
            tool.get('type') == 'image_generation' 
            for tool in model_args.get('tools', [])
        )
        
        if is_image_command:
            # Use ImageGenerator
            img_gen = ImageGenerator(provider=provider)
            
            # Extract image parameters from tools
            tool = next(tool for tool in model_args.get('tools', []) if tool.get('type') == 'image_generation')
            size = tool.get('size', '1024x1024')
            quality = tool.get('quality', 'auto')
            
            # Generate image
            image_data = img_gen.generate(text, size=size, quality=quality)
            
            # Save image with same naming logic as original q.py
            image_file = 'q_' + ''.join(c for c in text if c not in string.punctuation).replace(' ', '_') + '.png'
            with open(image_file, 'wb') as f:
                f.write(image_data)
            cprint(f'Image saved to {image_file}.', 'yellow', file=sys.stderr)
            
            # Save messages for follow-up commands (image generation format)
            messages.append({'type': 'image_generation_call', 'id': image_file})
            config._save_resource('messages', messages)
            
            text_response = None
            image_response = {'result': base64.b64encode(image_data).decode()}
        else:
            # Use TextGenerator for text generation
            from .config.models import Message, MessageRole, ModelParameters, GenerationRequest
            
            # Convert message format
            converted_messages = []
            for msg in messages:
                if 'role' in msg and 'content' in msg:
                    try:
                        role = MessageRole(msg['role'])
                        converted_messages.append(Message(role=role, content=msg['content']))
                    except ValueError:
                        # Handle unknown roles - skip or use as-is
                        continue
            
            # Create model parameters
            model_params = ModelParameters(
                model=model_args['model'],
                max_output_tokens=model_args['max_output_tokens'],
                temperature=model_args['temperature'],
                tools=model_args.get('tools')
            )
            
            # Create request
            request = GenerationRequest(
                messages=converted_messages,
                model_params=model_params,
                command_type="cli"
            )
            
            # Generate text
            response = provider.generate_text(request)
            text_response = response.text
            
            # Process response with original logic
            processor = ResponseProcessor()
            text_response = processor.process_text_response(text_response)
            
            # Save messages for follow-up commands
            messages.append({'role': 'assistant', 'content': text_response})
            config._save_resource('messages', messages)
            
            image_response = None

    except Exception as e:
        cprint(f'Error: {e}', 'red', file=sys.stderr)
        sys.exit(1)

    # Print output - exact same logic as original
    if opt_args.get('verbose', False):
        # Model parameters
        cprint('MODEL PARAMETERS:', 'red', file=sys.stderr)
        for arg in model_args:
            print(colored(f'{arg}:', 'green'), model_args[arg], file=sys.stderr)
        # Message history
        cprint('\n'+'MESSAGES:', 'red', file=sys.stderr)
        for message in messages:
            if message.get('role'):
                print(colored(f'{message["role"].capitalize()}:', 'green'), message['content'], file=sys.stderr)
            elif message.get('type'):
                print(colored(f'{message["type"]}:', 'green'), message['id'], file=sys.stderr)
    elif not image_response and text_response:
        print(text_response)

    # Copy text response to clipboard - exact same logic as original
    if not image_response and text_response and not opt_args.get('no-clip', False) and cmd_config.get('clip_output', False):
        try:
            pyperclip.copy(text_response)
            cprint(f'Output copied to clipboard.', 'yellow', file=sys.stderr)
        except pyperclip.PyperclipException:
            pass  # ignore clipboard errors


def print_help():
    """Print help text - exact same format as original q.py."""
    # Get commands in original format
    commands_list = []
    
    # Add default command first
    default_cmd = get_default_command()
    if default_cmd:
        cmd_config = default_cmd.get_command_config()
        commands_list.append(cmd_config)
    
    # Add other commands
    for command in list_commands():
        if command.flags:  # Skip default command (already added)
            cmd_config = command.get_command_config()
            commands_list.append(cmd_config)
    
    # Generate help text with exact same format as original
    tab_spaces, flag_len = 4, max(len(', '.join(cmd['flags'])) for cmd in commands_list + OPTIONS) + 2
    help_text = f'q {__version__} - {DESCRIPTION}'
    help_text += '\n\nUsage: ' + colored('q [command] TEXT [options]', 'green')
    help_text += '\n\nCommands (one required):\n'
    help_text += '\n'.join([
        ' '*tab_spaces + colored(f'{", ".join(cmd["flags"]) if cmd["flags"] else "TEXT":<{flag_len}}', 'green') + f'{cmd["description"]}' 
        for cmd in commands_list
    ])
    help_text += '\n\nOptions:\n'
    help_text += '\n'.join([
        ' '*tab_spaces + colored(f'{", ".join(opt["flags"]):<{flag_len}}', 'green') + f'{opt["description"]}' 
        for opt in OPTIONS
    ])

    print(help_text)


def main():
    """
    Main CLI entry point - maintains exact same behavior as original q.py main function.
    """
    # Fix ANSI escape codes on Windows
    just_fix_windows_console()

    # Validate custom commands
    validation_errors = validate_commands()
    if validation_errors:
        for error in validation_errors:
            cprint(f'Error: {error}', 'red', file=sys.stderr)
        sys.exit(1)

    # Get command line arguments
    args = sys.argv

    # Print help text if no arguments or -h/--help flag is provided
    if len(args) == 1 or args[1] in ['-h', '--help']:
        print_help()
        sys.exit(0)

    # Get all command flags
    all_commands = list_commands()
    cmd_flags = []
    for cmd in all_commands:
        cmd_flags.extend(cmd.flags)

    # Check if there is more than one command
    if len([arg for arg in args[1:] if arg in cmd_flags]) > 1:
        cprint(f'Error: Only one command may be provided.', 'red', file=sys.stderr)
        sys.exit(1)

    # Check if there is a command that is not the first argument
    if len([arg for arg in args[1:] if arg in cmd_flags]) == 1 and args[1] not in cmd_flags:
        cprint(f'Error: Command must be the first argument.', 'red', file=sys.stderr)
        sys.exit(1)

    # Check if the first argument is an invalid command
    if args[1].startswith('-') and args[1] not in cmd_flags:
        cprint(f'Error: Invalid command "{args[1]}".', 'red', file=sys.stderr)
        sys.exit(1)

    # Check if there is no text provided for a command
    if args[1] in cmd_flags and len(args) < 3:
        cprint(f'Error: No text provided.', 'red', file=sys.stderr)
        sys.exit(1)

    # Extract options and remove them from the text - exact same logic as original
    opt_args = {opt['name']: False for opt in OPTIONS}
    opt_flags = [flag for opt in OPTIONS for flag in opt['flags']]
    while args[-1].startswith('-') and args[-1] != '-':
        # Individual flags (e.g. -v -n)
        if args[-1] in opt_flags:
            flag = args.pop()
            for opt in OPTIONS:
                if flag in opt['flags']:
                    opt_args[opt['name']] = True
        # Combined flags (e.g. -vn)
        else:
            flags = args.pop()[1:]
            for flag in flags:
                for opt in OPTIONS:
                    if f'-{flag}' in opt['flags']:
                        opt_args[opt['name']] = True
                        break
                else:
                    cprint(f'Error: Invalid option "-{flag}".', 'red', file=sys.stderr)
                    sys.exit(1)

    # Mask stderr if stdout is being piped
    if not sys.stdout.isatty():
        sys.stderr = open(os.devnull, 'w')

    # Run command - exact same logic as original
    for cmd in all_commands:
        if args[1] in cmd.flags:
            cmd_config = cmd.get_command_config()
            run_command(cmd_config, ' '.join(args[2:]), **opt_args)
            sys.exit(0)
    # Run default command
    else:
        # Get default command
        default_cmd = get_default_command()
        if default_cmd:
            cmd_config = default_cmd.get_command_config()
            run_command(cmd_config, ' '.join(args[1:]), **opt_args)
        else:
            cprint(f'Error: No default command found.', 'red', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()