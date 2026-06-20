from __future__ import annotations

import asyncio
import contextlib
import os
import platform
import string
import subprocess
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import distro
import pyperclip
from termcolor import colored

from q import __version__
from q.providers import load_client_class

from ..agents import ChatAgent
from .models import Tier, resolve_model_arg
from .session import StateManager
from .terminal import InputError, format_response, qprint

# region Registry

COMMANDS: list[type[Command]] = []
OPTIONS: list[type[Flag]] = []


def get_default_command() -> type[Command]:
    char = StateManager.load_command_char()
    if char:
        for cmd in COMMANDS:
            if cmd.char == char:
                return cmd
    return TextCommand


# region Types

type Value = str | int | None
type ArgMap = dict[str, Value]


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

    tier: Tier
    client_str: str = "TextClient"
    system: str | None = None
    clip: bool = False

    async def execute(self) -> None:
        # resolve provider, model, and model args
        default_provider = StateManager.load_default_provider()
        provider, model, model_args = resolve_model_arg(self.args.get("m"), self.tier, default_provider)

        # create client dynamically
        client_class = load_client_class(provider, self.client_str)
        api_key = self.args.get("k") or StateManager.load_api_key(provider)
        client = client_class(api_key, model, **model_args)

        if "v" in self.args:
            qprint("MODEL PARAMETERS:", color="cyan", file=sys.stderr)
            qprint("model: ", color="green", file=sys.stderr, end="")
            qprint(f"{client.model} ({provider})", file=sys.stderr)
            if client.model_args:
                for k, v in client.model_args.items():
                    qprint(f"{k}: ", color="green", file=sys.stderr, end="")
                    qprint(f"{v}", file=sys.stderr)

        # create agent
        messages = [] if "n" in self.args else StateManager.load_messages()
        agent = ChatAgent(client, self.system, messages)
        if "z" in self.args:
            agent.drop_exchanges(self.args["z"])

        # prompt agent
        response = await agent.prompt(self.args[self.char])
        
        # save session
        StateManager.save_session(self.char, agent.messages)

        if "v" in self.args:
            qprint("\nMESSAGES:", color="cyan", file=sys.stderr)
            if agent.system:
                qprint("system: ", color="green", file=sys.stderr, end="")
                qprint(agent.system, file=sys.stderr)
            for msg in agent.messages:
                qprint(f"{msg.role.value}: ", color="green", file=sys.stderr, end="")
                qprint(msg.content, file=sys.stderr)

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
            if "v" not in self.args:
                qprint(response)
            
            # copy output to clipboard
            if self.clip:
                with contextlib.suppress(pyperclip.PyperclipException):
                    pyperclip.copy(response)
                    qprint("Copied to clipboard.", color="yellow", file=sys.stderr)


# region Commands


class TextCommand(AgentCommand):
    char = "t"
    desc = "text"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.MED
    system = ""


class ExplainCommand(AgentCommand):
    char = "e"
    desc = "explain"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.HIGH
    system = "You are a programming assistant. Given a shell command, code snippet, or technical concept, provide a concise and technical explanation. Assume the reader is an experienced developer. Avoid restating the code or command. Avoid explaining obvious syntax. Avoid breaking the answer into bullet points unless necessary. The response should be a single short paragraph optimized for clarity."


class CodeCommand(AgentCommand):
    char = "c"
    desc = "code"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.HIGH
    clip = True

    @property
    def system(self) -> str:
        return f"You are a coding assistant. Given a natural language description, generate a code snippet that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. Respond with only the code snippet, without explanations, additional text, or formatting. Assume the programming language is {StateManager.load_code_lang()} unless otherwise specified."


class ShellCommand(AgentCommand):
    char = "s"
    desc = "shell"
    value_type = ValueType.TEXT
    required = False
    tier = Tier.MED
    clip = True

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

    async def execute(self) -> None:
        # rerun and fix last command (requires shell integration)
        if self.args[self.char] is None:
            cmd = os.environ.get("Q_CMD", None)
            exit_code = os.environ.get("Q_EXIT", None)
            if cmd is None or exit_code is None:
                raise InputError(
                    "q -s without a prompt requires shell integration. Add to ~/.bashrc:\n"
                    '    q() { Q_EXIT=$? Q_CMD=$(fc -ln -1) command q "$@"; }'
                )
            cmd, exit_code = cmd.strip(), exit_code.strip()

            try:
                # run command and capture output
                proc = await asyncio.create_subprocess_shell(
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
                text = f"The command `{cmd}` failed with exit code {proc.returncode}. Fix it."
                if stderr:
                    text += f"\nSTDERR:\n{stderr.decode().strip()}"
                if stdout:
                    text += f"\nSTDOUT:\n{stdout.decode().strip()}"
            except TimeoutError:
                # kill long-running command
                proc.kill()
                text = f"The command `{cmd}` failed with exit code {exit_code}. Fix it."
            self.args[self.char] = text

        await super().execute()

    def process_response(self, response: str) -> None:
        # execute command
        if "x" in self.args:
            qprint(f"> {response}", color="green", file=sys.stderr)
            subprocess.run(response, shell=True)
        else:
            super().process_response(response)


class WebCommand(AgentCommand):
    char = "w"
    desc = "web"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.LOW
    client_str = "WebClient"
    system = "You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context, background, or links. The response should be less than a single sentence. Always search the internet."


class ImageCommand(AgentCommand):
    char = "i"
    desc = "image"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.MED
    client_str = "ImageClient"
    system = "Generate an image of the following description."

    def process_response(self, response: bytes) -> None:
        text = self.args[self.char].translate(str.maketrans("", "", string.punctuation)).replace(" ", "_")
        path = self.args.get("o") or f"q_{text}"
        path = path if path.lower().endswith(".png") else f"{path}.png"
        Path(path).write_bytes(response)
        qprint(f"Image saved to {path}", color="yellow", file=sys.stderr)


class HelpCommand(AgentCommand):
    char = "h"
    desc = "help"
    value_type = ValueType.TEXT
    required = False
    tier = Tier.LOW

    @property
    def system(self) -> str:
        cli_dir = Path(__file__).parent
        source_code = "\n\n".join((cli_dir / name).read_text() for name in Path(cli_dir).glob("*.py"))
        return (
            "You are `q`, a command-line LLM tool. Answer questions about usage based on the source code."
            f"\n\n{source_code}\n\n"
            "Be extremely concise. Answer in one line. Focus on usage."
            "Always surround code snippets, commands, flags, and paths with backticks."
        )

    async def execute(self) -> None:
        if self.args.get(self.char):
            await super().execute()
        else:
            qprint(self._help_text())

    def _help_text(self) -> str:
        command_color = "cyan"
        flags = []
        for f in sorted(COMMANDS + OPTIONS, key=lambda f: f.char):
            flag_arg = f.value_type.value or ""
            if flag_arg:
                flag_arg = f"<{flag_arg}>" if f.required else f"[{flag_arg}]"
            flag_str = f"    -{f.char}  {f.desc} {flag_arg}"
            flags.append(colored(flag_str, command_color if f in COMMANDS else "dark_grey"))

        lines = [
            f"q {__version__} - a command line programming agent",
            "",
            "Usage: q [-flag [value]] ...",
            "",
            "  Flags can be combined: -sx = -s -x",
            "  Use -- to disable remaining flag parsing.",
            f"  One {colored('command', command_color)} is required.",
            "",
            "Flags:",
            *flags,
        ]
        return "\n".join(lines)


# region Options


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


class KeyOption(Flag):
    char = "k"
    desc = "api key"
    value_type = ValueType.STR
    required = True


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


class UndoOption(Flag):
    char = "z"
    desc = "undo"
    value_type = ValueType.INT
    default = 1
