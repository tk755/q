import getpass
import sys

from colorama import just_fix_windows_console
from termcolor import colored

# fix Windows console to support ANSI codes
just_fix_windows_console()


class InputError(Exception):
    """Input validation error displayed without traceback."""


def qprint(*values: str, color: str | None = None, **kwargs):
    """Print values. Apply color if stream is an interactive terminal."""
    stream = kwargs.get("file", sys.stdout)
    if color and stream.isatty():
        values = tuple(colored(v, color, force_color=True) for v in values)
    print(*values, **kwargs)


def qinput(text: str = "", color: str | None = None, secret: bool = False) -> str:
    """Prompt user for input. No echo if secret=True."""
    if color:
        text = colored(text, color)
    if secret:
        return getpass.getpass(text)
    return input(text)
