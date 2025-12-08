import os
import platform
import re
import shutil
import string
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Any

import distro
import humanize
from termcolor import colored

from src import __version__
from src.providers import load_client_class
from .state import StateManager, Session
from .terminal import qprint
from ..agents import ChatAgent
from ..message import Role


class CommandError(Exception):
    pass


# region Registry

COMMANDS: list[type['Command']] = []
OPTIONS: list[type['Flag']] = []


def get_default_command() -> type['Command']:
    return TextCommand


def get_flag_lookup() -> dict[str, type['Flag']]:
    return {f.char: f for f in COMMANDS + OPTIONS}


# region Types

Value = str | int | None
ParsedArgs = dict[str, Value]


class ValueType(Enum):
    NONE = auto()
    TEXT = auto()
    STR = auto()
    INT = auto()


# region Helpers

async def prompt_agent(client_str: str, system: str, text: str, parsed_args: ParsedArgs, state: StateManager) -> Any:
    """Create and prompt an agent."""
    # resolve provider and model
    model_path = state.model
    if '/' not in model_path:
        raise CommandError(f"invalid model in config: '{model_path}' (expected provider/model)")
    if 'm' in parsed_args:
        model_arg = parsed_args['m']
        if '/' in model_arg:
            model_path = model_arg
        else:
            provider = model_path.split('/')[0]
            model_path = f"{provider}/{model_arg}"
    provider, model = model_path.split('/', 1)

    # dynamically create client
    client_class = load_client_class(provider, client_str)
    api_key = state.get_api_key(provider)
    client = client_class(api_key, model)

    # create agent
    agent = ChatAgent(client, system, state.messages)
    if 'z' in parsed_args:
        agent.drop_exchanges(parsed_args['z'])
    
    # prompt agent and update state
    response = await agent.prompt(text)
    state.messages = agent.messages
    return response


def _format_response(text: str, code_color: str = 'cyan') -> str:
    """Process LLM response for terminal display."""
    # shorten links from web search responses
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text).strip()

    # convert two-plus newlines into only two
    text = re.sub(r'\n{2,}', '\n\n', text)

    # remove formatting from response-level code blocks
    text = re.sub(r'^```.*?\n(.*)\n```$', r'\1', text, flags=re.DOTALL)

    # convert code blocks into colored text
    text = re.sub(r'```(?:\w+\n?)?(.*?)```', lambda m: colored(m.group(1).strip(), code_color), text, flags=re.DOTALL)

    # convert inline-code into colored text
    text = re.sub(r'`([^`]+)`', lambda m: colored(m.group(1), code_color), text)

    return text


# region Base Classes

class Flag:
    """Base class for CLI flags. Subclasses auto-register to OPTIONS."""
    char: str
    desc: str
    value_type: ValueType = ValueType.NONE
    required: bool = False
    default: Value = None

    def __init_subclass__(cls, **kwargs):
        """Auto-register subclass to OPTIONS if it defines a char."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'char'):
            OPTIONS.append(cls)


class Command(Flag):
    """Base class for CLI commands. Subclasses auto-register to COMMANDS."""

    def __init_subclass__(cls, **kwargs):
        """Move subclass from OPTIONS to COMMANDS if it defines a char."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'char'):
            OPTIONS.remove(cls)
            COMMANDS.append(cls)

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        """Execute command with option handling and output routing."""
        # pre-agent options
        if 'v' in parsed_args:
            pass # TODO: implement verbose logging
        if 'n' in parsed_args:
            state.new_session()

        # generate response
        response = await cls.generate_response(parsed_args, state)

        if response is None:
            return

        # post-agent options
        if 'j' not in parsed_args:
            response = _format_response(response)

        # output routing
        if 'o' in parsed_args:
            Path(parsed_args['o']).write_text(response)
            qprint(f"Response saved to {parsed_args['o']}", color='yellow', file=sys.stderr)
        else:
            qprint(response)

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str | None:
        """Generate command response. Return None if command handles its own output."""
        raise NotImplementedError


# region Commands

class TextCommand(Command):
    char = 't'
    desc = 'text'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = 'You are a helpful assistant.'
        text = parsed_args[cls.char]
        return await prompt_agent('TextClient', system, text, parsed_args, state)


class ExplainCommand(Command):
    char = 'e'
    desc = 'explain'
    value_type = ValueType.TEXT

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = 'You are a programming assistant. Given a shell command, code snippet, or technical concept, provide a concise and technical explanation. Assume the reader is an experienced developer. Avoid restating the code or command. Avoid explaining obvious syntax. Avoid breaking the answer into bullet points unless necessary. The response should be a single short paragraph optimized for clarity.'
        text = f'Explain: {parsed_args[cls.char]}'
        return await prompt_agent('TextClient', system, text, parsed_args, state)


class CodeCommand(Command):
    char = 'c'
    desc = 'code'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = f'You are a coding assistant. Given a natural language description, generate a code snippet that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. Respond with only the code snippet, without explanations, additional text, or formatting. Assume the programming language is {state.code_lang} unless otherwise specified.'
        text = f'Generate a code snippet to accomplish the following task: {parsed_args[cls.char]}. Respond only with the code, without explanation or additional text.'
        return await prompt_agent('TextClient', system, text, parsed_args, state)


class ShellCommand(Command):
    char = 's'
    desc = 'shell'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = f'You are a command-line assistant. Given a natural language task description, generate the simplest single shell command that accomplishes the task. Favor minimal, commonly available commands with no extra formatting or piping. Avoid commands that could delete, overwrite, or modify important files or system settings (e.g., rm -rf, dd, mkfs, chmod -R, chown, kill -9). Respond with only the command, without explanations, additional text, or formatting. System is running {cls._get_system_info()}.'
        text = f'Generate a single shell command to accomplish the following task: {parsed_args[cls.char]}. Respond with only the command, without explanation or additional text.'
        return await prompt_agent('TextClient', system, text, parsed_args, state)

    @classmethod
    def _get_system_info(cls) -> str:
        shell = os.environ.get('SHELL') or os.environ.get('COMSPEC')
        shell = os.path.basename(shell) if shell else ''

        system = platform.system()
        if system == 'Linux':
            try:
                system = distro.name(pretty=True)
            except ImportError:
                pass

        if shell:
            return f'{shell} on {system}'
        return system


class WebCommand(Command):
    char = 'w'
    desc = 'web'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = 'You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context, background, or links. The response should be less than a single sentence.'
        text = f'Fetch the following information: {parsed_args[cls.char]}.'
        return await prompt_agent('WebClient', system, text, parsed_args, state)


class ImageCommand(Command):
    char = 'i'
    desc = 'image'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        system = 'Generate an image of the following description.'
        text = parsed_args[cls.char]
        image = await prompt_agent('ImageClient', system, text, parsed_args, state)
        cls.save_image(parsed_args, image)
    
    @classmethod
    def save_image(cls, parsed_args: ParsedArgs, image: bytes) -> None:
        text = parsed_args[cls.char].translate(str.maketrans('', '', string.punctuation)).replace(' ', '_')
        path = parsed_args.get('o') or f'q_{text}'
        path = path if path.lower().endswith('.png') else f'{path}.png'
        Path(path).write_bytes(image)
        qprint(f'Image saved to {path}', color='yellow', file=sys.stderr)


class RetrievalCommand(Command):
    char = 'r'
    desc = 'retrieval'
    value_type = ValueType.TEXT

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        raise CommandError(f"-{cls.char} command not yet implemented")


class AgentCommand(Command):
    char = 'a'
    desc = 'agent'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        raise CommandError(f"-{cls.char} command not yet implemented")


class UserCommand(Command):
    char = 'u'
    desc = 'user command'
    value_type = ValueType.STR
    required = True

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        raise CommandError(f"-{cls.char} command not yet implemented")

class LoadCommand(Command):
    char = 'l'
    desc = 'load session'
    value_type = ValueType.INT

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        session_id = parsed_args.get(cls.char)
        if session_id is None:
            qprint(cls._format_sessions(state.list_sessions()))
            return
        if not state.load_session(session_id):
            raise CommandError(f"invalid session: {session_id}")
        qprint(f"loaded session {session_id}", color='yellow', file=sys.stderr)

    @classmethod
    def _format_sessions(cls, sessions: list[Session]) -> str:
        if not sessions:
            return "No sessions found."
        lines = [cls._format_session(s) for s in sessions]
        return "\n".join(lines)

    @classmethod
    def _format_session(cls, session: Session) -> str:
        age = humanize.naturaltime(session.updated) if session.updated else "unknown"

        # calculate max preview length based on terminal width
        term_width = shutil.get_terminal_size().columns
        prefix_len = len(f"  {session.id}. ")
        suffix_len = len(f" ({age})")
        max_len = max(20, term_width - prefix_len - suffix_len - 3)  # 3 for "..."

        preview = "(empty)"
        for msg in session.messages:
            if msg.role == Role.USER:
                preview = msg.content[:max_len] + "..." if len(msg.content) > max_len else msg.content
                break

        return f"  {colored(f'{session.id}.', 'yellow')} {preview} {colored(f'({age})', 'dark_grey')}"


class HelpCommand(Command):
    char = 'h'
    desc = 'help'
    value_type = ValueType.TEXT
    required = False

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        if parsed_args.get(cls.char):
            qprint(cls._help_prompt())
        else:
            qprint(cls._help_text())

    @classmethod
    def _help_prompt(cls) -> str:
        raise NotImplementedError
        
    @classmethod
    def _help_text(cls) -> str:
        commands = []
        options = []

        for f in sorted(COMMANDS + OPTIONS, key=lambda f: f.char):
            flag_str = f'-{f.char}'
            if f.value_type == ValueType.INT:
                flag_str += ' int '
            elif f.value_type == ValueType.STR:
                flag_str += ' str '
            elif f.value_type == ValueType.TEXT:
                flag_str += ' text'
            if f.value_type != ValueType.NONE and not f.required:
                flag_str += ' ?'

            flag_len = 11
            flag_fmt = colored(f"{flag_str:<{flag_len}}", "green")
            line = f'    {flag_fmt}{f.desc}'
            if f in COMMANDS:
                commands.append(line)
            else:
                options.append(line)

        text = f'q {__version__} - an LLM-powered programming copilot from the comfort of your command line'
        usage = colored('q [-flag [value]] ...', 'green')
        text += '\n\nUsage: ' + usage + '\n'
        text += '\n  Flags can be combined: -sx = -s -x'
        text += '\n  Use -- to disable remaining flag parsing.'
        text += '\n  One command is required.'
        text += '\n\nCommands:\n' + '\n'.join(commands)
        text += '\n\nOptions:\n' + '\n'.join(options)
        return text


# region Options

class BatchOption(Flag):
    char = 'b'
    desc = 'batch'
    value_type = ValueType.TEXT
    required = True


class DirectoryOption(Flag):
    char = 'd'
    desc = 'directory'
    value_type = ValueType.STR


class FileOption(Flag):
    char = 'f'
    desc = 'file'
    value_type = ValueType.STR
    required = True


class JsonOption(Flag):
    char = 'j'
    desc = 'json output'


class ModelOption(Flag):
    char = 'm'
    desc = 'model'
    value_type = ValueType.STR
    required = True


class NewSessionOption(Flag):
    char = 'n'
    desc = 'new session'


class OutputOption(Flag):
    char = 'o'
    desc = 'output'
    value_type = ValueType.STR
    required = True


class VerboseOption(Flag):
    char = 'v'
    desc = 'verbose'


class ExecuteOption(Flag):
    char = 'x'
    desc = 'execute shell'


class YesOption(Flag):
    char = 'y'
    desc = 'yes always'


class UndoOption(Flag):
    char = 'z'
    desc = 'undo'
    value_type = ValueType.INT
    default = 1
