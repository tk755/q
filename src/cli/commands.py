import importlib
import os
import platform
import re
import shutil
import sys
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

import distro
import humanize
from termcolor import colored

from src import __version__
from .state import StateManager, Session
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


# region Base Classes

Value = str | int | None
ParsedArgs = dict[str, Value]


class ValueType(Enum):
    NONE = auto()
    TEXT = auto()
    STR = auto()
    INT = auto()


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
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        """Execute command with pre/post option handling."""
        cls.pre_execute_options(parsed_args, state)
        result = await cls.execute(parsed_args, state)
        return cls.post_execute_options(result, parsed_args)

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        """Core command logic. Override in subclasses."""
        raise NotImplementedError

    @classmethod
    def pre_execute_options(cls, parsed_args: ParsedArgs, state: StateManager):
        """Process options that apply before execution."""
        if 'n' in parsed_args:
            state.new_session()

        if 'v' in parsed_args:
            print(f"[debug] provider: {state.provider}", file=sys.stderr)
            print(f"[debug] model: {state.model}", file=sys.stderr)
            print(f"[debug] session: {state.session_id}", file=sys.stderr)
            print(f"[debug] messages: {len(state.messages)}", file=sys.stderr)

    @classmethod
    def post_execute_options(cls, result: str, parsed_args: ParsedArgs) -> str:
        """Process options that apply after execution."""
        if 'j' not in parsed_args:
            result = cls._format_response(result)
        if 'o' in parsed_args:
            Path(parsed_args['o']).write_text(result)
        return result

    @classmethod
    def _format_response(cls, text: str, code_color: str = 'cyan') -> str:
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

    @classmethod
    def get_agent(cls, parsed_args: ParsedArgs, state: StateManager, system_prompt: str = '', capability: str = 'text'):
        """Create a ChatAgent with resolved provider, model, and capability."""
        # resolve provider and model: -m flag > cls.model > config defaults
        provider = state.provider
        model = getattr(cls, 'model', None) or state.model
        if 'm' in parsed_args:
            model_spec = parsed_args['m']
            if '/' in model_spec:
                provider, model = model_spec.split('/', 1)
                provider = provider.lower()
            else:
                model = model_spec

        # get provider module
        api_key = state.get_api_key(provider)
        try:
            _provider = importlib.import_module(f'src.providers.{provider}')
        except ModuleNotFoundError:
            raise CommandError(f"Unknown provider: {provider}") from None

        # create client by capability
        client_class = getattr(_provider, f'{capability.title()}Client', None)
        if client_class is None:
            raise CommandError(f"Capability '{capability}' not supported by {provider}")
        client = client_class(api_key, model)

        # create agent
        agent = ChatAgent(
            client,
            messages=state.messages,
            system_prompt=system_prompt
        )

        # handle -z
        if 'z' in parsed_args:
            agent.drop_exchanges(parsed_args['z'])

        return agent

    @classmethod
    def read_file(cls, parsed_args: ParsedArgs) -> str | None:
        """Read file content from -f flag if present."""
        if 'f' in parsed_args:
            return Path(parsed_args['f']).read_text()
        return None


class PromptCommand(Command):
    """Base for commands that prompt an LLM with a system message."""
    system: str
    model: str | None = None

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        """Prompt the agent and update session messages."""
        agent = cls.get_agent(parsed_args, state, cls.system)
        response = await agent.prompt(parsed_args[cls.char])
        state.messages = agent.messages
        return response


# region Commands

class TextCommand(PromptCommand):
    char ='t'
    desc = 'text'
    value_type = ValueType.TEXT
    required = True
    system = 'You are a helpful assistant.'


class CodeCommand(PromptCommand):
    char = 'c'
    desc = 'code'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        language = state.code_lang
        system = f'You are a coding assistant. Given a natural language description, generate a code snippet that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. Respond with only the code snippet, without explanations, additional text, or formatting. Assume the programming language is {language} unless otherwise specified.'

        text = parsed_args[cls.char]
        file_content = cls.read_file(parsed_args)
        if file_content:
            text = f"{text}\n\nFile content:\n```\n{file_content}\n```"
        prompt = f'Generate a code snippet to accomplish the following task: {text}. Respond only with the code, without explanation or additional text.'

        agent = cls.get_agent(parsed_args, state, system)
        response = await agent.prompt(prompt)
        state.messages = agent.messages
        return response


class ExplainCommand(PromptCommand):
    char = 'e'
    desc = 'explain'
    value_type = ValueType.TEXT
    model = 'gpt-4.1-mini'
    system = 'You are a programming assistant. Given a shell command, code snippet, or technical concept, provide a concise and technical explanation. Assume the reader is an experienced developer. Avoid restating the code or command. Avoid explaining obvious syntax. Avoid breaking the answer into bullet points unless necessary. The response should be a single short paragraph optimized for clarity.'

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        text = parsed_args.get(cls.char) or ''
        file_content = cls.read_file(parsed_args)
        if file_content:
            text = f"{file_content}\n{text}" if text else file_content
        prompt = f'Explain: {text}'

        agent = cls.get_agent(parsed_args, state, cls.system)
        response = await agent.prompt(prompt)
        state.messages = agent.messages
        return response


class ShellCommand(PromptCommand):
    char = 's'
    desc = 'shell'
    value_type = ValueType.TEXT
    required = True
    model = 'gpt-4.1-mini'

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = f'You are a command-line assistant. Given a natural language task description, generate the simplest single shell command that accomplishes the task. Favor minimal, commonly available commands with no extra formatting or piping. Avoid commands that could delete, overwrite, or modify important files or system settings (e.g., rm -rf, dd, mkfs, chmod -R, chown, kill -9). Respond with only the command, without explanations, additional text, or formatting. System is running {cls._get_system_info()}.'

        text = parsed_args[cls.char]
        prompt = f'Generate a single shell command to accomplish the following task: {text}. Respond with only the command, without explanation or additional text.'

        agent = cls.get_agent(parsed_args, state, system)
        response = await agent.prompt(prompt)
        state.messages = agent.messages
        return response

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


class WebCommand(PromptCommand):
    char = 'w'
    desc = 'web'
    value_type = ValueType.TEXT
    required = True
    system = 'You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context, background, or links. The response should be less than a single sentence.'

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        text = parsed_args[cls.char]
        prompt = f'Fetch the following information: {text}.'

        agent = cls.get_agent(parsed_args, state, cls.system, capability='web')
        response = await agent.prompt(prompt)
        state.messages = agent.messages
        return response


class HelpCommand(Command):
    char ='h'
    desc = 'help'
    value_type = ValueType.TEXT
    required = False

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
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


class LoadCommand(Command):
    char ='l'
    desc = 'load session'
    value_type = ValueType.INT

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        cls.pre_execute_options(parsed_args, state)
        session_id = parsed_args.get(cls.char)
        if session_id is None:
            return cls.format_sessions(state.list_sessions())
        if not state.load_session(session_id):
            raise CommandError(f"invalid session: {session_id}")
        return f"Loaded session {session_id}"

    @classmethod
    def format_sessions(cls, sessions: list[Session]) -> str:
        if not sessions:
            return "No sessions found."
        lines = [cls.format_session(s) for s in sessions]
        return "\n".join(lines)

    @classmethod
    def format_session(cls, session: Session) -> str:
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


class AgentCommand(Command):
    char ='a'
    desc = 'agent'
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        raise CommandError("Command not implemented yet")


class ImageCommand(Command):
    char = 'i'
    desc = 'image'
    value_type = ValueType.TEXT
    required = True
    model = 'gpt-image-1'

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        agent = cls.get_agent(parsed_args, state, capability='image')
        image_bytes = await agent.prompt(parsed_args[cls.char])

        # save image to file
        output_path = parsed_args.get('o')
        if not output_path:
            output_path = 'output.png'
        Path(output_path).write_bytes(image_bytes)
        state.messages = agent.messages
        return f"Image saved to {output_path}"


class RetrievalCommand(Command):
    char ='r'
    desc = 'retrieval'
    value_type = ValueType.TEXT

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        raise CommandError("Command not implemented yet")


class UserCommand(Command):
    char ='u'
    desc = 'user command'
    value_type = ValueType.STR
    required = True

    @classmethod
    async def execute(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        raise CommandError("Command not implemented yet")


# region Options

class BatchOption(Flag):
    char ='b'
    desc = 'batch'
    value_type = ValueType.TEXT
    required = True


class DirectoryOption(Flag):
    char ='d'
    desc = 'directory'
    value_type = ValueType.STR


class FileOption(Flag):
    char ='f'
    desc = 'file'
    value_type = ValueType.STR
    required = True


class JsonOption(Flag):
    char ='j'
    desc = 'json output'


class ModelOption(Flag):
    char ='m'
    desc = 'model'
    value_type = ValueType.STR
    required = True


class NewSessionOption(Flag):
    char ='n'
    desc = 'new session'


class OutputOption(Flag):
    char ='o'
    desc = 'output'
    value_type = ValueType.STR
    required = True


class VerboseOption(Flag):
    char ='v'
    desc = 'verbose'


class ExecuteOption(Flag):
    char ='x'
    desc = 'execute shell'


class YesOption(Flag):
    char ='y'
    desc = 'yes always'


class UndoOption(Flag):
    char ='z'
    desc = 'undo'
    value_type = ValueType.INT
    default = 1
