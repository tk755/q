from __future__ import annotations

import contextlib
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

from ..agents import ChatAgent
from ..message import Role
from .state import Session, StateManager
from .terminal import qprint


class CommandError(Exception):
    pass


# region Registry

COMMANDS: list[type[Command]] = []
OPTIONS: list[type[Flag]] = []


def get_default_command() -> type[Command]:
    return TextCommand


def get_flag_lookup() -> dict[str, type[Flag]]:
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


def _format_response(text: str, code_color: str = "cyan") -> str:
    """Process LLM response for terminal display."""
    # shorten links from web search responses
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text).strip()

    # convert two-plus newlines into only two
    text = re.sub(r"\n{2,}", "\n\n", text)

    # remove formatting from response-level code blocks
    text = re.sub(r"^```.*?\n(.*)\n```$", r"\1", text, flags=re.DOTALL)

    # convert code blocks into colored text
    text = re.sub(r"```(?:\w+\n?)?(.*?)```", lambda m: colored(m.group(1).strip(), code_color), text, flags=re.DOTALL)

    # convert inline-code into colored text
    text = re.sub(r"`([^`]+)`", lambda m: colored(m.group(1), code_color), text)

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
        if hasattr(cls, "char"):
            OPTIONS.append(cls)


class Command(Flag):
    """Base class for CLI commands. Subclasses auto-register to COMMANDS."""

    def __init_subclass__(cls, **kwargs):
        """Move subclass from OPTIONS to COMMANDS if it defines a char."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "char"):
            OPTIONS.remove(cls)
            COMMANDS.append(cls)

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        """Execute command."""


class AgentCommand(Command):
    """Base class for commands that prompt an agent."""

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        # pre-agent options
        if "v" in parsed_args:
            pass  # TODO
        if "n" in parsed_args:
            state.new_session()

        # generate response
        response = await cls.generate_response(parsed_args, state)

        if response is None:
            return

        # post-agent options
        if "j" not in parsed_args:
            response = _format_response(response)

        # output routing
        if "o" in parsed_args:
            Path(parsed_args["o"]).write_text(response)
            qprint(f"Response saved to {parsed_args['o']}", color="yellow", file=sys.stderr)
        else:
            qprint(response)

    @classmethod
    async def prompt_agent(
        cls, client_str: str, system: str | None, parsed_args: ParsedArgs, state: StateManager
    ) -> Any:
        """Create and prompt an agent."""
        # resolve provider and model
        model_path = state.model
        if "/" not in model_path:
            raise CommandError(f"invalid model in config: '{model_path}' (expected provider/model)")
        if "m" in parsed_args:
            model_arg = parsed_args["m"]
            if "/" in model_arg:
                model_path = model_arg
            else:
                provider = model_path.split("/")[0]
                model_path = f"{provider}/{model_arg}"
        provider, model = model_path.split("/", 1)

        # dynamically create client
        client_class = load_client_class(provider, client_str)
        api_key = state.get_api_key(provider)
        client = client_class(api_key, model)

        # create agent
        agent = ChatAgent(client, system, state.messages)
        if "z" in parsed_args:
            agent.drop_exchanges(parsed_args["z"])

        # prompt agent and update state
        response = await agent.prompt(parsed_args[cls.char])
        state.messages = agent.messages
        return response

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str | None:
        """Generate command response. Return None if command handles its own output."""


# region Commands


class TextCommand(AgentCommand):
    char = "t"
    desc = "text"
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        return await cls.prompt_agent("TextClient", None, parsed_args, state)


class ExplainCommand(AgentCommand):
    char = "e"
    desc = "explain"
    value_type = ValueType.TEXT

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = "You are a programming assistant. Given a shell command, code snippet, or technical concept, provide a concise and technical explanation. Assume the reader is an experienced developer. Avoid restating the code or command. Avoid explaining obvious syntax. Avoid breaking the answer into bullet points unless necessary. The response should be a single short paragraph optimized for clarity."
        return await cls.prompt_agent("TextClient", system, parsed_args, state)


class CodeCommand(AgentCommand):
    char = "c"
    desc = "code"
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = f"You are a coding assistant. Given a natural language description, generate a code snippet that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. Respond with only the code snippet, without explanations, additional text, or formatting. Assume the programming language is {state.code_lang} unless otherwise specified."
        return await cls.prompt_agent("TextClient", system, parsed_args, state)


class ShellCommand(AgentCommand):
    char = "s"
    desc = "shell"
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = f"You are a command-line assistant. Given a description, generate the simplest single shell command that accomplishes the task. Favor minimal, commonly available commands with no extra formatting or piping. Avoid commands that could delete, overwrite, or modify important files or system settings (e.g., rm -rf, dd, mkfs, chmod -R, chown, kill -9). Respond with only the command, without explanations, additional text, or formatting. System is running {cls._get_system_info()}."
        return await cls.prompt_agent("TextClient", system, parsed_args, state)

    @classmethod
    def _get_system_info(cls) -> str:
        shell = os.environ.get("SHELL") or os.environ.get("COMSPEC")
        shell = Path(shell).name if shell else ""

        system = platform.system()
        if system == "Linux":
            with contextlib.suppress(ImportError):
                system = distro.name(pretty=True)

        if shell:
            return f"{shell} on {system}"
        return system


class WebCommand(AgentCommand):
    char = "w"
    desc = "web"
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> str:
        system = "You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context, background, or links. The response should be less than a single sentence. Always search the internet."
        return await cls.prompt_agent("WebClient", system, parsed_args, state)


class ImageCommand(AgentCommand):
    char = "i"
    desc = "image"
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def generate_response(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        system = "Generate an image given a description."
        image = await cls.prompt_agent("ImageClient", system, parsed_args, state)
        cls.save_image(parsed_args, image)

    @classmethod
    def save_image(cls, parsed_args: ParsedArgs, image: bytes) -> None:
        text = parsed_args[cls.char].translate(str.maketrans("", "", string.punctuation)).replace(" ", "_")
        path = parsed_args.get("o") or f"q_{text}"
        path = path if path.lower().endswith(".png") else f"{path}.png"
        Path(path).write_bytes(image)
        qprint(f"Image saved to {path}", color="yellow", file=sys.stderr)


class RetrievalCommand(Command):
    char = "r"
    desc = "retrieval"
    value_type = ValueType.TEXT

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        raise CommandError(f"-{cls.char} not yet implemented")


class AutoCommand(Command):
    char = "a"
    desc = "auto"
    value_type = ValueType.TEXT
    required = True

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        raise CommandError(f"-{cls.char} not yet implemented")


class UserCommand(Command):
    char = "u"
    desc = "user command"
    value_type = ValueType.STR
    required = True

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        raise CommandError(f"-{cls.char} not yet implemented")


class LoadCommand(Command):
    char = "l"
    desc = "load session"
    value_type = ValueType.INT

    @classmethod
    async def dispatch(cls, parsed_args: ParsedArgs, state: StateManager) -> None:
        session_id = parsed_args.get(cls.char)
        if session_id is None:
            cls._print_sessions(state.list_sessions(), state.session_id)
            return
        if not state.load_session(session_id):
            raise CommandError(f"invalid session: {session_id}")
        qprint(f"Loaded session {session_id}", color="yellow", file=sys.stderr)

    @classmethod
    def _print_sessions(cls, sessions: list[Session], current_id: int) -> None:
        if not sessions:
            qprint("No sessions found.")
            return

        term_width = shutil.get_terminal_size().columns
        for s in sessions:
            age = humanize.naturaltime(s.updated) if s.updated else "unknown"
            prefix_len = len(f"    {s.id}.  ")
            suffix_len = len(f" ({age})")
            max_len = max(20, term_width - prefix_len - suffix_len - 5)  # at least -3 for ellipsis

            preview = "(empty)"
            for msg in reversed(s.messages):
                if msg.role == Role.USER:
                    preview = msg.content[:max_len] + "..." if len(msg.content) > max_len else msg.content
                    break

            line = f"    {s.id}.  {preview} ({age})"
            qprint(line if s.id == current_id else colored(line, "dark_grey"))


class HelpCommand(Command):
    char = "h"
    desc = "help"
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
        raise CommandError("-h <text> not yet implemented")

    @classmethod
    def _help_text(cls) -> str:
        usage_color = "green"
        command_color = "cyan"
        option_color = "dark_grey"

        flags = []
        for f in sorted(COMMANDS + OPTIONS, key=lambda f: f.char):
            flag_arg = ""
            if f.value_type == ValueType.INT:
                flag_arg += "N"
            elif f.value_type == ValueType.STR:
                flag_arg += "str"
            elif f.value_type == ValueType.TEXT:
                flag_arg += "text"
            if f.value_type != ValueType.NONE:
                if f.required:
                    flag_arg = f"<{flag_arg}>"
                else:
                    flag_arg = f"[{flag_arg}]"

            flag_str = f"-{f.char}  {f.desc} {flag_arg}"
            flag_fmt = colored(flag_str, command_color if f in COMMANDS else option_color)
            flags.append(f"    {flag_fmt:<{10}}")

        text = f"q {__version__} - a command line programming agent"
        usage = colored("q [-flag [value]] ...", usage_color)
        text += "\n\nUsage: " + usage + "\n"
        text += "\n  Flags can be combined: -sx = -s -x"
        text += "\n  Use -- to disable remaining flag parsing."
        text += "\n  One " + colored("command", command_color) + " is required."
        text += "\n\nFlags:\n" + "\n".join(flags)
        return text


# region Options


class BatchOption(Flag):
    char = "b"
    desc = "batch"
    value_type = ValueType.TEXT
    required = True


class DirectoryOption(Flag):
    char = "d"
    desc = "directory"
    value_type = ValueType.STR


class FileOption(Flag):
    char = "f"
    desc = "file"
    value_type = ValueType.STR
    required = True


class JsonOption(Flag):
    char = "j"
    desc = "json"


class ModelOption(Flag):
    char = "m"
    desc = "model"
    value_type = ValueType.STR
    required = True


class NewSessionOption(Flag):
    char = "n"
    desc = "new session"


class OutputOption(Flag):
    char = "o"
    desc = "output"
    value_type = ValueType.STR
    required = True


class VerboseOption(Flag):
    char = "v"
    desc = "verbose"


class ExecuteOption(Flag):
    char = "x"
    desc = "execute"


class YesOption(Flag):
    char = "y"
    desc = "accept all"


class UndoOption(Flag):
    char = "z"
    desc = "undo"
    value_type = ValueType.INT
    default = 1
