from __future__ import annotations

import contextlib
import os
import platform
import re
import string
import sys
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import Any

import distro
from termcolor import colored

from src import __version__
from src.providers import load_client_class

from ..agents import ChatAgent
from .session import SessionManager
from .terminal import qprint


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

    async def execute(self) -> None:
        # pre-agent options
        if "v" in self.args:
            pass  # TODO
        if "n" in self.args:
            SessionManager.new_session()

        # generate response
        response = await self.generate_response()

        if response is None:
            return

        # post-agent options
        if "j" not in self.args:
            response = _format_response(response)

        # output routing
        if "o" in self.args:
            Path(self.args["o"]).write_text(response)
            qprint(f"Response saved to {self.args['o']}", color="yellow", file=sys.stderr)
        else:
            qprint(response)

    async def prompt_agent(self, client_str: str, system: str | None) -> Any:
        """Create and prompt an agent."""
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

        # dynamically create client
        client_class = load_client_class(provider, client_str)
        api_key = SessionManager.load_api_key(provider)
        client = client_class(api_key, model)

        # create agent
        agent = ChatAgent(client, system, SessionManager.load_messages())
        if "z" in self.args:
            agent.drop_exchanges(self.args["z"])

        # prompt agent and save messages
        response = await agent.prompt(self.args[self.char])
        SessionManager.save_messages(agent.messages)
        return response

    @abstractmethod
    async def generate_response(self) -> str | None: ...


# region Commands


class TextCommand(AgentCommand):
    char = "t"
    desc = "text"
    value_type = ValueType.TEXT
    required = True

    async def generate_response(self) -> str:
        return await self.prompt_agent("TextClient", None)


class ExplainCommand(AgentCommand):
    char = "e"
    desc = "explain"
    value_type = ValueType.TEXT

    async def generate_response(self) -> str:
        system = "You are a programming assistant. Given a shell command, code snippet, or technical concept, provide a concise and technical explanation. Assume the reader is an experienced developer. Avoid restating the code or command. Avoid explaining obvious syntax. Avoid breaking the answer into bullet points unless necessary. The response should be a single short paragraph optimized for clarity."
        return await self.prompt_agent("TextClient", system)


class CodeCommand(AgentCommand):
    char = "c"
    desc = "code"
    value_type = ValueType.TEXT
    required = True

    async def generate_response(self) -> str:
        system = f"You are a coding assistant. Given a natural language description, generate a code snippet that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. Respond with only the code snippet, without explanations, additional text, or formatting. Assume the programming language is {SessionManager.load_code_lang()} unless otherwise specified."
        return await self.prompt_agent("TextClient", system)


class ShellCommand(AgentCommand):
    char = "s"
    desc = "shell"
    value_type = ValueType.TEXT
    required = True

    async def generate_response(self) -> str:
        system = f"You are a command-line assistant. Given a description, generate the simplest single shell command that accomplishes the task. Favor minimal, commonly available commands with no extra formatting or piping. Avoid commands that could delete, overwrite, or modify important files or system settings (e.g., rm -rf, dd, mkfs, chmod -R, chown, kill -9). Respond with only the command, without explanations, additional text, or formatting. System is running {self._get_system_info()}."
        return await self.prompt_agent("TextClient", system)

    def _get_system_info(self) -> str:
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

    async def generate_response(self) -> str:
        system = "You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context, background, or links. The response should be less than a single sentence. Always search the internet."
        return await self.prompt_agent("WebClient", system)


class ImageCommand(AgentCommand):
    char = "i"
    desc = "image"
    value_type = ValueType.TEXT
    required = True

    async def generate_response(self) -> None:
        system = "Generate an image given a description."
        image = await self.prompt_agent("ImageClient", system)
        self.save_image(image)

    def save_image(self, image: bytes) -> None:
        text = self.args[self.char].translate(str.maketrans("", "", string.punctuation)).replace(" ", "_")
        path = self.args.get("o") or f"q_{text}"
        path = path if path.lower().endswith(".png") else f"{path}.png"
        Path(path).write_bytes(image)
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
            qprint(SessionManager.format_session_list())
            return
        if not SessionManager.switch_session(session_id):
            raise QError(f"invalid session: {session_id}")
        qprint(f"Loaded session {session_id}", color="yellow", file=sys.stderr)


class HelpCommand(Command):
    char = "h"
    desc = "help"
    value_type = ValueType.TEXT
    required = False

    async def execute(self) -> None:
        if self.args.get(self.char):
            qprint(self._help_prompt())
        else:
            qprint(self._help_text())

    def _help_prompt(self) -> str:
        raise QError("-h <text> not yet implemented")

    def _help_text(self) -> str:
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
