import getpass
import re
import sys

from colorama import just_fix_windows_console
from termcolor import colored

# fix Windows console to support ANSI codes
just_fix_windows_console()


def _sanitize_text(text: str) -> str:
    """Prepare text for printing, stripping ANSI codes for non-terminals."""
    # check if output is a terminal
    if sys.stdout.isatty():
        return text

    # strip ANSI color codes
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def qprint(*values: str, color: str | None = None, **kwargs):
    """Print values, stripping ANSI codes for non-terminals."""
    if color:
        values = [colored(v, color) for v in values]
    values = [_sanitize_text(v) for v in values]
    print(*values, **kwargs)


def qinput(text: str = "", color: str | None = None, secret: bool = False) -> str:
    """Prompt user for input. No echo if secret=True."""
    if color:
        text = colored(text, color)
    if secret:
        return getpass.getpass(_sanitize_text(text))
    return input(_sanitize_text(text))
