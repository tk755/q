from __future__ import annotations

import asyncio
import contextlib
import os
import platform
import re
import string
import subprocess
import sys
import textwrap
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

import distro
import pyperclip
from flatten_dict import flatten
from termcolor import colored

from q import Client, Role, __version__, list_providers, load_client_class

from .models import Tier, lookup
from .session import StateManager
from .terminal import InputError, qprint

# region Registry


FLAG_MAP: dict[str, type[Flag]] = {}


def get_default_command() -> type[Command]:
    char = StateManager.load_command_char()
    if char in FLAG_MAP and issubclass(FLAG_MAP[char], Command):
        return FLAG_MAP[char]
    return TextCommand


# region Types


class ValueType(Enum):
    NONE = None
    INT = "n"
    STR = "str"
    STR_LIST = "str+"
    TEXT = "text"


# region Base Classes


class Flag(ABC):
    """Base class for CLI flags."""

    char: str
    desc: str
    value_type: ValueType = ValueType.NONE
    value_required: bool = False
    value_default: Any = None
    requires: tuple[type[Command], ...] = ()

    def __init_subclass__(cls, **kwargs):
        """Auto-register concrete subclass to FLAG_MAP."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "char"):
            FLAG_MAP[cls.char] = cls


class Command(Flag):
    """Base class for CLI commands."""

    def __init__(self, value: str | None, opts: dict[type[Flag], Any]):
        self.value = value
        self.opts = opts

    @abstractmethod
    async def execute(self) -> None: ...


class LLMCommand(Command):
    """Base class for commands that prompt an LLM."""

    tier: Tier
    client_name: str = "TextClient"
    system: str | None = None
    clip: bool = False

    async def execute(self) -> None:
        # resolve model override
        if ModelOption in self.opts:
            provider, model, model_args = ModelOption.resolve(self.opts[ModelOption], self.client_name, self.tier)
        else:
            provider = StateManager.default_provider()
            model, model_args = lookup(provider, self.client_name, self.tier)

        # create client with prior history
        api_key = self.opts.get(KeyOption) or StateManager.load_api_key(provider)
        messages = [] if NewOption in self.opts else StateManager.load_messages()
        client = load_client_class(provider, self.client_name)(api_key, model, messages=messages, **model_args)
        if UndoOption in self.opts:
            client.drop_exchanges(self.opts[UndoOption])

        # build prompt and image list
        file_text, images = "", None
        if FileOption in self.opts:
            file_text, images = FileOption.resolve(self.opts[FileOption])
        prompt = await self.build_prompt(file_text)

        # pre-prompt debug output
        if VerboseOption in self.opts:
            VerboseOption.pre_prompt_debug(provider, client, self.system, prompt, images)

        # send request to LLM and wait for response
        response = await client.generate(prompt, self.system, images)

        # post-prompt debug output
        if VerboseOption in self.opts:
            VerboseOption.post_prompt_debug()

        # process response
        self.process_response(response)

        # save session
        StateManager.save_session(self.char, client.messages)

    async def build_prompt(self, file_text: str) -> str:
        """Build the user prompt string."""
        return "\n\n".join(filter(None, [file_text, self.value]))

    def process_response(self, response: str) -> None:
        """Format response and route output."""
        formatted_response = self._format_text_response(response.strip())
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
    def _format_code_response(text: str) -> str:
        """Unwrap a response-level code fence or inline-code span."""
        text = re.sub(r"^```.*?\n(.*)\n```$", r"\1", text, flags=re.DOTALL)
        return re.sub(r"^`([^`\n]+)`$", r"\1", text)

    @staticmethod
    def _format_text_response(text: str) -> str:
        """Normalize the formatting of an LLM text response."""
        text = LLMCommand._format_code_response(text)

        # convert two-plus newlines into only two
        text = re.sub(r"\n{2,}", "\n\n", text)

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
    value_required = True
    tier = Tier.LOW
    system = ""


class ExplainCommand(LLMCommand):
    char = "e"
    desc = "explain code/concept"
    value_type = ValueType.TEXT
    value_required = True
    tier = Tier.LOW
    system = "Give an expert the shortest and maximally information-dense explanation in one paragraph, no filler."


class WebCommand(LLMCommand):
    char = "w"
    desc = "search the web"
    value_type = ValueType.TEXT
    value_required = True
    tier = Tier.LOW
    client_name = "WebClient"
    system = "Search the web and reply with only the answer, as a bare value such as a name, number, or date, with nothing else: no full sentence, no restatement, no context, no explanation."

    @staticmethod
    def _format_text_response(text: str) -> str:
        return LLMCommand._format_text_response(WebCommand._format_web_response(text))

    @staticmethod
    def _format_web_response(text: str) -> str:
        """Shorten links from web search responses."""
        return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


class CodeCommand(LLMCommand):
    char = "c"
    desc = "generate code"
    value_type = ValueType.TEXT
    value_required = True
    tier = Tier.MED
    clip = True

    @property
    def system(self) -> str:
        code_lang = self.opts.get(LanguageOption) or StateManager.default_code_lang()
        return f"Generate the most minimal, idiomatic {code_lang} code that fully solves the task, implementing the function or class it calls for. No over-engineering or unrequested features. Prefer the standard library to reinventing it. Output only the code."


class ShellCommand(LLMCommand):
    char = "s"
    desc = "generate shell command"
    value_type = ValueType.TEXT
    value_required = False
    tier = Tier.MED
    clip = True

    @property
    def system(self) -> str:
        return f"Generate the single simplest, most direct idiomatic shell command for the task on {self._get_system_info()}. Output only the command. Never use destructive commands (rm -rf, dd, mkfs, chmod -R, chown, kill -9)."

    async def build_prompt(self, file_text: str) -> str:
        """Build prompt to fix last shell command if no prompt is provided."""
        if self.value:
            return await super().build_prompt(file_text)

        # get last shell command
        cmd = os.environ.get("Q_CMD", None)
        exit_code = os.environ.get("Q_EXIT", None)
        if cmd is None or exit_code is None:
            rc_file = "~/.zshrc" if "zsh" in os.environ.get("SHELL", "") else "~/.bashrc"
            try:
                pyperclip.copy(self._shell_hook())
                qprint(f"Shell hook copied to clipboard; paste it in {rc_file}", color="yellow", file=sys.stderr)
            except pyperclip.PyperclipException:
                qprint(f"Copy the following shell hook to {rc_file}:\n\n{self._shell_hook()}\n", color="yellow", file=sys.stderr)
            raise InputError(f"-{self.char} requires a shell hook to fix last command")

        cmd = cmd.strip()
        if not cmd:
            raise InputError(f"-{self.char} has nothing to fix; no command found")
        if exit_code == "0":
            raise InputError(f"-{self.char} has nothing to fix; last command succeeded")

        # run shell command and capture output
        stderr = stdout = b""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            exit_code = proc.returncode
        except TimeoutError:
            proc.kill()

        # prompt to fix last shell command
        text = f"The command `{cmd}` failed with exit code {exit_code}. Fix it."
        if stderr:
            text += f"\nSTDERR:\n{stderr.decode().strip()}"
        if stdout:
            text += f"\nSTDOUT:\n{stdout.decode().strip()}"
        return text

    def process_response(self, response: str) -> None:
        """Execute shell command if applicable."""
        response = self._format_code_response(response.strip())
        if ExecuteOption in self.opts:
            qprint(f"> {response}", color="green", file=sys.stderr)
            exec_path = os.environ.get("Q_EXEC")
            if exec_path:
                # shell hook installed; run in parent shell
                Path(exec_path).write_text(response)
            else:
                # no shell hook; run in subprocess
                subprocess.run(response, shell=True)
        else:
            super().process_response(response)

    @staticmethod
    def _shell_hook() -> str:
        return textwrap.dedent(r"""
            # shell hook for q -s
            q() {
              local rc=$? f=${TMPDIR:-/tmp}/q-exec.$$ p
              read -r p < <(fc -ln -1); [[ $p =~ ^q(\ |$) ]] && p=$(cat "$f" 2>/dev/null); : >"$f"
              Q_EXIT=$rc Q_CMD="$p" Q_EXEC="$f" command q "$@"; rc=$?
              [[ -s $f ]] && { eval "$(<"$f")"; rc=$?; }
              return "$rc"
            }
        """).strip()

    @staticmethod
    def _get_system_info() -> str:
        shell = os.environ.get("SHELL") or os.environ.get("COMSPEC")
        shell = Path(shell).name if shell else ""

        sys_name = platform.system()
        if sys_name == "Linux":
            with contextlib.suppress(ImportError):
                sys_name = distro.name(pretty=True)

        if shell:
            return f"{sys_name} using {shell}"
        return sys_name


class HelpCommand(LLMCommand):
    char = "h"
    desc = "get help with q"
    value_type = ValueType.TEXT
    value_required = False
    tier = Tier.LOW

    ACCENT_COLOR = "light_blue"
    DIM_COLOR = "dark_grey"

    @property
    def system(self) -> str:
        cli_dir = Path(__file__).parent
        source_code = "\n\n".join((cli_dir / name).read_text() for name in Path(cli_dir).glob("*.py"))
        return f"You are `q`, and this is your source code.\n\n{source_code}\n\nUse the above source code to answer questions about CLI usage. Focus on CLI usage, not implementation details. Be extremely concise. Answer the question directly without providing additional context. Always surround code snippets, commands, flags, and paths with backticks."

    async def execute(self) -> None:
        if self.value:
            await super().execute()
        else:
            qprint(self._help_text(VerboseOption in self.opts))

    @classmethod
    def _help_text(cls, verbose: bool = False) -> str:
        """Return full help text for the CLI."""
        blocks = [
            cls._help_text_usage(),
            cls._help_text_flags(verbose),
            cls._help_text_providers(verbose)
        ]
        return "\n\n".join("\n".join(block) for block in blocks)

    @classmethod
    def _help_text_usage(cls) -> list[str]:
        return [
            f"{colored('Version:', attrs=['bold'])} {__version__}",
            f"{colored('Usage:', attrs=['bold'])} q [{colored('-flag', cls.ACCENT_COLOR)} [{colored('value', cls.DIM_COLOR)}]] ...",
            "",
            "  Flags can be combined: -sx = -s -x",
            "  Use -- to disable remaining flag parsing.",
            "  Commands are mutually exclusive.",
        ]

    @classmethod
    def _help_text_flags(cls, verbose: bool = False) -> list[str]:
        type_col_len = max(len(f"[{flag.value_type.value}]") for flag in FLAG_MAP.values())
        desc_col_len = max(len(flag.desc) for flag in FLAG_MAP.values())

        command_rows, option_rows = [], []
        for flag in sorted(FLAG_MAP.values(), key=lambda flag: flag.char):
            char = colored(f"-{flag.char}", cls.ACCENT_COLOR)

            accent_word = flag.__name__.removesuffix("Command").removesuffix("Option").lower()
            desc = flag.desc.ljust(desc_col_len).replace(accent_word, colored(accent_word, cls.ACCENT_COLOR))

            value_type = flag.value_type.value or ""
            if value_type:
                if flag.value_default:
                    value_type += f"={flag.value_default}"
                value_type = f"<{value_type}>" if flag.value_required else f"[{value_type}]"
            value_type = colored(value_type.ljust(type_col_len), cls.DIM_COLOR)

            row = f"  {char}  {value_type}  {desc}"
            if verbose:
                if hasattr(flag, "tier"):
                    tier = colored(f"{flag.tier.value} tier", cls.DIM_COLOR)
                    row += f"  {tier}"
            row = row.rstrip()

            if issubclass(flag, Command):
                command_rows.append(row)
            else:
                option_rows.append(row)

        return [
            colored("Commands:", attrs=["bold"]),
            *command_rows,
            "",
            colored("Options:", attrs=["bold"]),
            *option_rows,
        ]

    @classmethod
    def _help_text_providers(cls, verbose: bool = False) -> list[str]:
        items = []
        for provider in list_providers():
            item = colored(provider, cls.ACCENT_COLOR)
            if verbose and provider == StateManager.default_provider():
                item += colored(" (default)", cls.DIM_COLOR)
            items.append(item)
        return [
            colored("Providers:", attrs=["bold"]),
            f"  {', '.join(items)}",
        ]


class ImageCommand(LLMCommand):
    char = "i"
    desc = "generate image"
    value_type = ValueType.TEXT
    value_required = True
    tier = Tier.MED
    client_name = "ImageClient"
    system = "Generate an image."

    def process_response(self, response: bytes) -> None:
        """Save image to disk."""
        text = self.value.translate(str.maketrans("", "", string.punctuation)).replace(" ", "_")
        path = Path(self.opts.get(OutputOption) or f"q_{text}")
        if not path.suffix:
            path = path.with_suffix(f".{Client._sniff_mime(response).split('/')[-1]}")
        path.write_bytes(response)
        qprint(f"Image saved to {path}", color="yellow", file=sys.stderr)


# region Options


class FileOption(Flag):
    char = "f"
    desc = "add file content"
    value_type = ValueType.STR_LIST
    value_required = True

    @classmethod
    def resolve(cls, paths: list[str]) -> tuple[str, list[bytes]]:
        """Resolve a list of files into text content and bytes."""
        contents, images = [], []
        for path in paths:
            try:
                data = Path(path).expanduser().read_bytes()
            except OSError as e:
                raise InputError(f"cannot read '{path}': {e.strerror.lower()}") from None
            with contextlib.suppress(ValueError):
                Client._sniff_mime(data)
                images.append(data)
                continue
            with contextlib.suppress(UnicodeDecodeError):
                text = data.decode("utf-8")
                contents.append(f'<file path="{path}">\n{text.rstrip("\n")}\n</file>')
                continue
            raise InputError(f"cannot read '{path}': not valid UTF-8 text or image file")
        return "\n\n".join(contents), images


class KeyOption(Flag):
    char = "k"
    desc = "override API key"
    value_type = ValueType.STR
    value_required = True


class LanguageOption(Flag):
    char = "l"
    desc = "override code language"
    value_type = ValueType.STR
    value_required = True
    requires = (CodeCommand,)


class ModelOption(Flag):
    char = "m"
    desc = "override model"
    value_type = ValueType.STR
    value_required = True

    @classmethod
    def resolve(cls, value: str, client_name: str, tier: Tier) -> tuple[str, str, dict]:
        """Resolve a model flag value to (provider, model_name, model_args)."""
        tiers = {t.value for t in Tier}

        # provider:tier/model
        if ":" in value:
            provider, suffix = value.split(":", 1)
            if provider not in list_providers():
                raise InputError(f"invalid provider: {provider}")
            # provider:tier (e.g. "openai:high")
            if suffix in tiers:
                return provider, *lookup(provider, client_name, Tier(suffix))
            # provider:model (e.g. "openai:gpt-4.1-nano")
            return provider, suffix, {}

        # provider (e.g. "openai")
        if value in list_providers():
            return value, *lookup(value, client_name, tier)

        # tier (e.g. "high")
        if value in tiers:
            provider = StateManager.default_provider()
            return provider, *lookup(provider, client_name, Tier(value))

        raise InputError(f"cannot resolve model: {value}")


class NewOption(Flag):
    char = "n"
    desc = "new conversation"


class OutputOption(Flag):
    char = "o"
    desc = "output path"
    value_type = ValueType.STR
    value_required = True


class VerboseOption(Flag):
    char = "v"
    desc = "verbose output"

    PRIMARY_COLOR = "light_blue"
    SECONDARY_COLOR = "green"

    @classmethod
    def pre_prompt_debug(cls, provider: str, client: Client, system: str | None, prompt: str, images: list[bytes] | None = None) -> None:
        qprint("MODEL PARAMETERS:", color=cls.PRIMARY_COLOR, file=sys.stderr)
        qprint("model:", color=cls.SECONDARY_COLOR, file=sys.stderr, end=" ")
        qprint(f"{provider}:{client.model}", file=sys.stderr)
        if client.model_args:
            for k, v in flatten(client.model_args, reducer="dot").items():
                qprint(f"{k}:", color=cls.SECONDARY_COLOR, file=sys.stderr, end=" ")
                qprint(f"{v}", file=sys.stderr)
        if system:
            qprint("\nSYSTEM:", color=cls.PRIMARY_COLOR, file=sys.stderr)
            qprint(system, file=sys.stderr)
        qprint("\nMESSAGES:", color=cls.PRIMARY_COLOR, file=sys.stderr)
        for message in client.messages:
            end = "\n" if "\n" in message.text else " "
            qprint(f"{message.role.value}:", color=cls.SECONDARY_COLOR, file=sys.stderr, end=end)
            if message.images:
                qprint(f"{message.text} [{len(message.images)} image{'s' if len(message.images) > 1 else ''}]".strip(), file=sys.stderr)
            else:
                qprint(message.text, file=sys.stderr)
        end = "\n" if "\n" in prompt else " "
        qprint(f"{Role.USER.value}:", color=cls.SECONDARY_COLOR, file=sys.stderr, end=end)
        if images:
            qprint(f"{prompt} [{len(images)} image{'s' if len(images) > 1 else ''}]".strip(), file=sys.stderr)
        else:
            qprint(prompt, file=sys.stderr)

    @classmethod
    def post_prompt_debug(cls) -> None:
        qprint("\nRESPONSE:", color=cls.PRIMARY_COLOR, file=sys.stderr)


class ExecuteOption(Flag):
    char = "x"
    desc = "execute shell command"
    requires = (ShellCommand,)


class UndoOption(Flag):
    char = "z"
    desc = "undo exchanges"
    value_type = ValueType.INT
    value_default = 1


# region Reserved Flags


"""
class AgentCommand(Command):
    char = "a"
    desc = "delegate to agent"
    value_type = ValueType.STR
    value_required = True
    tier = Tier.HIGH


class BatchOption(Flag):
    char = "b"
    desc = "batch process inputs"
    value_type = ValueType.STR
    value_required = True


class DirectoryOption(Flag):
    char = "d"
    desc = "add directory layout"
    value_type = ValueType.STR
    value_default = "."

    @classmethod
    def get_layout(cls, path: str) -> str:
        raise NotImplementedError()


class G_Option(Flag):
    char = "g"
    desc = "unknown"

class JsonOption(Flag):
    char = "j"
    desc = "output in JSON"


class ParametersOption(Flag):
    char = "p"
    desc = "override model parameters"
    value_type = ValueType.TEXT
    value_required = True


class Q_Option(Flag):
    char = "q"
    desc = "unknown"


class RetrievalCommand(Command):
    char = "r"
    desc = "retrieval-augmented generation"
    value_type = ValueType.STR
    value_required = True
    tier = Tier.MED


class UnsafeOption(Flag):
    char = "u"
    desc = "unsafe shell command"


class Y_Option(Flag):
    char = "y"
    desc = "unknown"
"""
