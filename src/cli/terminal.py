import getpass
import re
import sys

from colorama import just_fix_windows_console
from termcolor import colored

# fix Windows console to support ANSI codes
just_fix_windows_console()


def is_terminal() -> bool:
    """Check if the output is a terminal."""
    return sys.stdout.isatty()


def strip_ansi(text: str) -> str:
    """Strip ANSI color codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def qprint(*values: str, color: str | None = None, **kwargs):
    """Print values, stripping ANSI codes for non-terminals."""
    if color:
        values = tuple(colored(v, color) for v in values)
    if not is_terminal():
        values = tuple(strip_ansi(v) for v in values)
    print(*values, **kwargs)


def qinput(text: str = "", color: str | None = None, secret: bool = False) -> str:
    """Prompt user for input. No echo if secret=True."""
    if color:
        text = colored(text, color)
    if not is_terminal():
        text = strip_ansi(text)
    if secret:
        return getpass.getpass(text)
    return input(text)


def format_response(text: str, code_color: str = "cyan") -> str:
    """Format LLM response for terminal display."""
    # shorten links from web search responses
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text).strip()

    # convert two-plus newlines into only two
    text = re.sub(r"\n{2,}", "\n\n", text)

    # remove formatting from response-level code blocks
    text = re.sub(r"^```.*?\n(.*)\n```$", r"\1", text, flags=re.DOTALL)

    if is_terminal():
        # convert code blocks into colored text
        text = re.sub(r"```(?:\w+\n?)?(.*?)```", lambda m: colored(m.group(1).strip(), code_color), text, flags=re.DOTALL)

        # convert inline-code into colored text
        text = re.sub(r"`([^`]+)`", lambda m: colored(m.group(1), code_color), text)

    return text
