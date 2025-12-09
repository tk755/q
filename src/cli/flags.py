from __future__ import annotations

import contextlib
import os
import platform
import shutil
import string
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import distro
import humanize
from termcolor import colored

from src import __version__
from src.providers import load_client_class

from ..agents import ChatAgent
from ..message import Role
from .session import SessionManager
from .terminal import format_response, qprint


class QError(Exception):
    pass


# region Registry

COMMANDS: list[type[Command]] = []
OPTIONS: list[type[Flag]] = []


def get_default_command() -> type[Command]:
    return TextCommand


# region Types

Value = str | int | None
ArgMap = dict[str, Value]


class ValueType(Enum):
    NONE = None
    TEXT = "text"
    STR = "str"
    INT = "N"


# region Base Classes


class Flag(ABC):
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

    def __init__(self, args: ArgMap):
        self.args = args

    def __init_subclass__(cls, **kwargs):
        """Move subclass from OPTIONS to COMMANDS if it defines a char."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "char"):
            OPTIONS.remove(cls)
            COMMANDS.append(cls)

    @abstractmethod
    async def execute(self) -> None: ...


class AgentCommand(Command):
    """Base class for commands that prompt an agent."""

    client_str: str = "TextClient"
    system: str | None = None

    async def execute(self) -> None:
        if "v" in self.args:
            pass  # TODO
        if "n" in self.args:
            SessionManager.new_session()

        # resolve provider and model
        model_path = SessionManager.load_model()
        if "/" not in model_path:
            raise QError(f"invalid model in config: '{model_path}' (expected provider/model)")
        if "m" in self.args:
            model_arg = self.args["m"]
            if "/" in model_arg:
                model_path = model_arg
            else:
                provider = model_path.split("/")[0]
                model_path = f"{provider}/{model_arg}"
        provider, model = model_path.split("/", 1)

        # create client dynamically
        client_class = load_client_class(provider, self.client_str)
        api_key = SessionManager.load_api_key(provider)
        client = client_class(api_key, model)

        # create agent
        agent = ChatAgent(client, self.system, SessionManager.load_messages())
        if "z" in self.args:
            agent.drop_exchanges(self.args["z"])

        # prompt agent and save session
        response = await agent.prompt(self.args[self.char])
        SessionManager.save_messages(agent.messages)

        # process response
        self.process_response(response)

    def process_response(self, response: str) -> None:
        """Format response and route output."""
        if "j" not in self.args:
            response = format_response(response)
        if "o" in self.args:
            Path(self.args["o"]).write_text(response)
            qprint(f"Response saved to {self.args['o']}", color="yellow", file=sys.stderr)
        else:
            qprint(response)


# region Commands


class TextCommand(AgentCommand):
    char = "t"
    desc = "text"
    value_type = ValueType.TEXT
    required = True


class ExplainCommand(AgentCommand):
    char = "e"
    desc = "explain"
    value_type = ValueType.TEXT
    system = "You are a programming assistant. Given a shell command, code snippet, or technical concept, provide a concise and technical explanation. Assume the reader is an experienced developer. Avoid restating the code or command. Avoid explaining obvious syntax. Avoid breaking the answer into bullet points unless necessary. The response should be a single short paragraph optimized for clarity."


class CodeCommand(AgentCommand):
    char = "c"
    desc = "code"
    value_type = ValueType.TEXT
    required = True

    @property
    def system(self) -> str:
        return f"You are a coding assistant. Given a natural language description, generate a code snippet that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. Respond with only the code snippet, without explanations, additional text, or formatting. Assume the programming language is {SessionManager.load_code_lang()} unless otherwise specified."


class ShellCommand(AgentCommand):
    char = "s"
    desc = "shell"
    value_type = ValueType.TEXT
    required = True

    @property
    def system(self) -> str:
        return f"You are a command-line assistant. Given a description, generate the simplest single shell command that accomplishes the task. Favor minimal, commonly available commands with no extra formatting or piping. Avoid commands that could delete, overwrite, or modify important files or system settings (e.g., rm -rf, dd, mkfs, chmod -R, chown, kill -9). Respond with only the command, without explanations, additional text, or formatting. System is running {self._get_system_info()}."

    def _get_system_info(self) -> str:
        shell = os.environ.get("SHELL") or os.environ.get("COMSPEC")
        shell = Path(shell).name if shell else ""

        sys_name = platform.system()
        if sys_name == "Linux":
            with contextlib.suppress(ImportError):
                sys_name = distro.name(pretty=True)

        if shell:
            return f"{shell} on {sys_name}"
        return sys_name


class WebCommand(AgentCommand):
    char = "w"
    desc = "web"
    value_type = ValueType.TEXT
    required = True
    client_str = "WebClient"
    system = "You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context, background, or links. The response should be less than a single sentence. Always search the internet."


class ImageCommand(AgentCommand):
    char = "i"
    desc = "image"
    value_type = ValueType.TEXT
    required = True
    client_str = "ImageClient"
    system = "Generate an image of the following description."

    def process_response(self, response: bytes) -> None:
        text = self.args[self.char].translate(str.maketrans("", "", string.punctuation)).replace(" ", "_")
        path = self.args.get("o") or f"q_{text}"
        path = path if path.lower().endswith(".png") else f"{path}.png"
        Path(path).write_bytes(response)
        qprint(f"Image saved to {path}", color="yellow", file=sys.stderr)


class RetrievalCommand(Command):
    char = "r"
    desc = "retrieval"
    value_type = ValueType.TEXT

    async def execute(self) -> None:
        raise QError(f"-{self.char} not yet implemented")


class AutoCommand(Command):
    char = "a"
    desc = "auto"
    value_type = ValueType.TEXT
    required = True

    async def execute(self) -> None:
        raise QError(f"-{self.char} not yet implemented")


class UserCommand(Command):
    char = "u"
    desc = "user command"
    value_type = ValueType.STR
    required = True

    async def execute(self) -> None:
        raise QError(f"-{self.char} not yet implemented")


class LoadCommand(Command):
    char = "l"
    desc = "load session"
    value_type = ValueType.INT

    async def execute(self) -> None:
        session_id = self.args.get(self.char)
        if session_id is None:
            self._print_session_list()
        elif not SessionManager.switch_session(session_id):
            raise QError(f"invalid session: {session_id}")
        else:
            qprint(f"Loaded session {session_id}", color="yellow", file=sys.stderr)

    def _print_session_list(self) -> None:
        sessions = SessionManager.list_sessions()
        if not sessions:
            qprint("No sessions found.")
            return

        current_id = SessionManager.load_session_id()
        term_width = shutil.get_terminal_size().columns

        for s in sessions:
            age = humanize.naturaltime(s.updated) if s.updated else "unknown"
            prefix_len = len(f"    {s.id}.  ")
            suffix_len = len(f" ({age})")
            max_len = max(20, term_width - prefix_len - suffix_len - 5)

            preview = "(empty)"
            for msg in reversed(s.messages):
                if msg.role == Role.USER:
                    preview = msg.content[:max_len] + "..." if len(msg.content) > max_len else msg.content
                    break

            line = f"    {s.id}.  {preview} ({age})"
            color = None if s.id == current_id else "dark_grey"
            qprint(line, color=color)


class HelpCommand(Command):
    char = "h"
    desc = "help"
    value_type = ValueType.TEXT
    required = False

    async def execute(self) -> None:
        if self.args.get(self.char):
            self._print_help_prompt()
        else:
            self._print_help()

    def _print_help_prompt(self) -> None:
        raise QError("-h <text> not yet implemented")

    def _print_help(self) -> None:
        usage_color = "green"
        command_color = "cyan"
        option_color = "dark_grey"

        flags = []
        for f in sorted(COMMANDS + OPTIONS, key=lambda f: f.char):
            flag_arg = f.value_type.value or ""
            if flag_arg:
                flag_arg = f"<{flag_arg}>" if f.required else f"[{flag_arg}]"

            flag_str = f"-{f.char}  {f.desc} {flag_arg}"
            flag_fmt = colored(flag_str, command_color if f in COMMANDS else option_color)
            flags.append(f"    {flag_fmt:<{10}}")

        qprint(f"q {__version__} - a command line programming agent")
        qprint()
        qprint("Usage:", colored("q [-flag [value]] ...", usage_color))
        qprint()
        qprint("  Flags can be combined: -sx = -s -x")
        qprint("  Use -- to disable remaining flag parsing.")
        qprint("  One", colored("command", command_color), "is required.")
        qprint()
        qprint("Flags:")
        for flag in flags:
            qprint(flag)


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
