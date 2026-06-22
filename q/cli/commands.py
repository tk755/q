from __future__ import annotations

import asyncio
import contextlib
import os
import platform
import re
import string
import subprocess
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import distro
import pyperclip
from flatten_dict import flatten
from termcolor import colored

from q import __version__
from q.providers import load_client_class

from ..agents import ChatAgent
from ..message import Role
from .models import Tier, resolve_model_flag
from .session import StateManager
from .terminal import InputError, qprint

# region Registry


FLAG_MAP: dict[str, type[Flag]] = {}
COMMAND_MAP: dict[str, type[Command]] = {}


def get_default_command() -> type[Command]:
    char = StateManager.load_command_char()
    if char in COMMAND_MAP:
        return COMMAND_MAP[char]
    return TextCommand


# region Types

type FlagValue = str | int | None


class ValueType(Enum):
    NONE = None
    TEXT = "text"
    STR = "str"
    INT = "N"


# region Base Classes


class Flag(ABC):
    """Base class for CLI flags."""

    char: str
    desc: str
    value_type: ValueType = ValueType.NONE
    required: bool = False
    default: FlagValue = None

    def __init_subclass__(cls, **kwargs):
        """Auto-register concrete subclass to FLAG_MAP."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "char"):
            FLAG_MAP[cls.char] = cls


class Command(Flag):
    """Base class for CLI commands."""

    def __init__(self, value: FlagValue, opts: dict[type[Flag], FlagValue]):
        self.value = value
        self.opts = opts

    def __init_subclass__(cls, **kwargs):
        """Auto-register concrete subclass to COMMAND_MAP."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "char"):
            COMMAND_MAP[cls.char] = cls

    @abstractmethod
    async def execute(self) -> None: ...


class LLMCommand(Command):
    """Base class for commands that prompt an LLM."""

    tier: Tier
    client_name: str = "TextClient"
    system: str | None = None
    clip: bool = False

    async def execute(self) -> None:
        # resolve provider, model, and model args
        default_provider = StateManager.default_provider()
        provider, model, model_args = resolve_model_flag(self.opts.get(ModelOption), self.tier, default_provider)

        # create client dynamically
        client_class = load_client_class(provider, self.client_name)
        api_key = self.opts.get(KeyOption) or StateManager.load_api_key(provider)
        client = client_class(api_key, model, **model_args)

        # create agent
        messages = [] if NewOption in self.opts else StateManager.load_messages()
        agent = ChatAgent(client, self.system, messages)
        if UndoOption in self.opts:
            agent.drop_exchanges(self.opts[UndoOption])

        # verbose output
        if VerboseOption in self.opts:
            qprint("MODEL PARAMETERS:", color="light_blue", file=sys.stderr)
            qprint("model: ", color="green", file=sys.stderr, end="")
            qprint(f"{provider}:{client.model}", file=sys.stderr)
            if client.model_args:
                for k, v in flatten(client.model_args, reducer="dot").items():
                    qprint(f"{k}: ", color="green", file=sys.stderr, end="")
                    qprint(f"{v}", file=sys.stderr)
            if agent.system:
                qprint("\nSYSTEM:", color="light_blue", file=sys.stderr)
                qprint(agent.system, file=sys.stderr)
            qprint("\nMESSAGES:", color="light_blue", file=sys.stderr)
            for message in agent.messages:
                qprint(f"{message.role.value}: ", color="green", file=sys.stderr, end="")
                qprint(message.content, file=sys.stderr)
            qprint(f"{Role.USER.value}: ", color="green", file=sys.stderr, end="")
            qprint(self.value, file=sys.stderr)
            qprint("\nRESPONSE:", color="light_blue", file=sys.stderr)

        # send prompt and receive response
        response = await agent.prompt(self.value)
        self.process_response(response)

        # save session
        StateManager.save_session(self.char, agent.messages)

    def process_response(self, response: str) -> None:
        """Format response and route output."""
        formatted_response = self._format_text_response(response)
        if OutputOption in self.opts:
            path = self.opts[OutputOption]
            Path(path).write_text(formatted_response)
            qprint(f"Response saved to {path}", color="yellow", file=sys.stderr)
        else:
            self._print_text_response(formatted_response)

            # copy output to clipboard
            if self.clip:
                with contextlib.suppress(pyperclip.PyperclipException):
                    pyperclip.copy(formatted_response)
                    qprint("Copied to clipboard.", color="yellow", file=sys.stderr)

    @staticmethod
    def _format_text_response(text: str) -> str:
        """Normalize the formatting of an LLM text response."""
        # shorten links from web search responses
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text).strip()

        # convert two-plus newlines into only two
        text = re.sub(r"\n{2,}", "\n\n", text)

        # remove formatting from response-level code blocks
        text = re.sub(r"^```.*?\n(.*)\n```$", r"\1", text, flags=re.DOTALL)

        return text

    @staticmethod
    def _print_text_response(text: str, code_color: str = "cyan", emphasis_color: str = "magenta") -> None:
        """Print an LLM text response to stdout, replacing formatting symbols with colors."""
        if sys.stdout.isatty():
            # convert code blocks into colored text
            text = re.sub(
                r"```(?:\w+\n?)?(.*?)```", lambda m: colored(m.group(1).strip(), code_color), text, flags=re.DOTALL
            )

            # convert inline-code into colored text
            text = re.sub(r"`([^`]+)`", lambda m: colored(m.group(1), code_color), text)

            # convert bold text into colored text
            text = re.sub(r"\*\*([^*]+)\*\*", lambda m: colored(m.group(1), emphasis_color), text)

            # convert italic text into colored text
            text = re.sub(r"\*([^*]+)\*", lambda m: colored(m.group(1), emphasis_color), text)

        qprint(text)


# region Commands


class TextCommand(LLMCommand):
    char = "t"
    desc = "generate text"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.MED
    system = ""


class ExplainCommand(LLMCommand):
    char = "e"
    desc = "explain code/concept"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.HIGH
    system = "You are a programming assistant. Given a shell command, code snippet, or technical concept, provide a concise and technical explanation. Assume the reader is an experienced developer. Avoid restating the code or command. Avoid explaining obvious syntax. Avoid breaking the answer into bullet points unless necessary. The response should be a single short paragraph optimized for clarity."


class CodeCommand(LLMCommand):
    char = "c"
    desc = "generate code"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.HIGH
    clip = True

    @property
    def system(self) -> str:
        code_lang = self.opts.get(LanguageOption) or StateManager.default_code_lang()
        return f"You are a coding assistant. Given a natural language description, generate a code snippet that accomplishes the requested task. The code should be correct, efficient, concise, and idiomatic. Respond with only the code snippet, without explanations, additional text, or formatting. Use the {code_lang} programming language."


class ShellCommand(LLMCommand):
    char = "s"
    desc = "generate shell command"
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
        # rerun and fix last shell command (requires shell integration)
        if self.value is None:
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
            self.value = text

        await super().execute()

    def process_response(self, response: str) -> None:
        # execute command
        if ExecuteOption in self.opts:
            qprint(f"> {response}", color="green", file=sys.stderr)
            subprocess.run(response, shell=True)
        else:
            super().process_response(response)


class WebCommand(LLMCommand):
    char = "w"
    desc = "search the web"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.LOW
    client_name = "WebClient"
    system = "You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context or background. The response should be less than a single sentence. Always search the internet."


class ImageCommand(LLMCommand):
    char = "i"
    desc = "generate image"
    value_type = ValueType.TEXT
    required = True
    tier = Tier.MED
    client_name = "ImageClient"
    system = "Generate an image of the following description."

    def process_response(self, response: bytes) -> None:
        text = self.value.translate(str.maketrans("", "", string.punctuation)).replace(" ", "_")
        path = self.opts.get(OutputOption) or f"q_{text}"
        path = path if path.lower().endswith(".png") else f"{path}.png"
        Path(path).write_bytes(response)
        qprint(f"Image saved to {path}", color="yellow", file=sys.stderr)


class HelpCommand(LLMCommand):
    char = "h"
    desc = "get help with q"
    value_type = ValueType.TEXT
    required = False
    tier = Tier.LOW

    @staticmethod
    def help_text(verbose: bool = False) -> str:
        accent_color = "light_blue"
        dim_color = "dark_grey"

        type_col_len = max(len(flag.value_type.value or "") for flag in FLAG_MAP.values()) + 2
        desc_col_len = max(len(flag.desc) for flag in FLAG_MAP.values()) if verbose else 0
        tier_col_len = max(len(flag.tier.value) for flag in FLAG_MAP.values() if hasattr(flag, "tier"))

        command_rows, option_rows = [], []
        for flag in sorted(FLAG_MAP.values(), key=lambda flag: flag.char):
            char = colored(f"-{flag.char}", accent_color)

            accent_word = flag.__name__.removesuffix("Command").removesuffix("Option").lower()
            desc = flag.desc.ljust(desc_col_len).replace(accent_word, colored(accent_word, accent_color))

            value_type = flag.value_type.value or ""
            if value_type:
                if flag.default:
                    value_type += f"={flag.default}"
                value_type = f"<{value_type}>" if flag.required else f"[{value_type}]"
            value_type = colored(value_type.ljust(type_col_len), dim_color)

            row = f"  {char}  {value_type}  {desc}"
            if verbose:
                if hasattr(flag, "tier"):
                    tier = colored(flag.tier.value.rjust(tier_col_len), dim_color)
                    row += f"  {tier}"

            row = row.rstrip()

            if issubclass(flag, Command):
                command_rows.append(row)
            else:
                option_rows.append(row)

        lines = [
            f"{colored('Version:', attrs=['bold'])} {__version__}",
            f"{colored('Usage:', attrs=['bold'])} q [{colored('-flag', accent_color)} [{colored('value', dim_color)}]] ...",
            "",
            "  Flags can be combined: -sx = -s -x",
            "  Use -- to disable remaining flag parsing.",
            "  Commands are mutually exclusive.",
            "",
            colored("Commands:", attrs=["bold"]),
            *command_rows,
            "",
            colored("Options:", attrs=["bold"]),
            *option_rows,
        ]

        if verbose:
            unused_flags = {f"-{char}" for char in string.ascii_lowercase if char not in FLAG_MAP}
            lines += [
                "",
                colored("Unused:", attrs=["bold"]),
                "  " + colored(", ".join(sorted(unused_flags)), accent_color),
            ]

        return "\n".join(lines)

    @property
    def system(self) -> str:
        cli_dir = Path(__file__).parent
        source_code = "\n\n".join((cli_dir / name).read_text() for name in Path(cli_dir).glob("*.py"))
        return (
            "You are `q`, and this is your source code."
            f"\n\n{source_code}\n\n"
            "Use the above source code to answer questions about CLI usage. "
            "Focus on CLI usage, not implementation details. "
            "Be extremely concise. Answer the question directly without providing additional context. "
            "Always surround code snippets, commands, flags, and paths with backticks."
        )

    async def execute(self) -> None:
        if not self.value:
            qprint(self.help_text(VerboseOption in self.opts))
        else:
            await super().execute()


# region Options


class KeyOption(Flag):
    char = "k"
    desc = "override API key"
    value_type = ValueType.STR
    required = True


class LanguageOption(Flag):
    char = "l"
    desc = "override code language"
    value_type = ValueType.STR
    required = True


class ModelOption(Flag):
    char = "m"
    desc = "override model"
    value_type = ValueType.STR
    required = True


class NewOption(Flag):
    char = "n"
    desc = "new session"


class OutputOption(Flag):
    char = "o"
    desc = "output path"
    value_type = ValueType.STR
    required = True


class VerboseOption(Flag):
    char = "v"
    desc = "verbose output"


class ExecuteOption(Flag):
    char = "x"
    desc = "execute shell command"


class UndoOption(Flag):
    char = "z"
    desc = "undo exchanges"
    value_type = ValueType.INT
    default = 1


# region Reserved Flags


"""
class AgentCommand(Command):
    char = "a"
    desc = "delegate to agent"
    value_type = ValueType.STR
    required = True
    tier = Tier.HIGH


class BatchOption(Flag):
    char = "b"
    desc = "batch process inputs"
    value_type = ValueType.STR
    required = True


class DirectoryOption(Flag):
    char = "d"
    desc = "add directory layout"
    value_type = ValueType.STR


class FileOption(Flag):
    char = "f"
    desc = "add file content"
    value_type = ValueType.STR
    required = True


class JsonOption(Flag):
    char = "j"
    desc = "output in JSON"


class ParametersOption(Flag):
    char = "p"
    desc = "override model parameters"
    value_type = ValueType.TEXT
    required = True


class RetrievalCommand(Command):
    char = "r"
    desc = "retrieval-augmented generation"
    value_type = ValueType.STR
    required = True
    tier = Tier.MED


class UserCommand(Command):
    char = "u"
    desc = "user command"
    value_type = ValueType.STR
    required = True
    tier = Tier.MED
"""
