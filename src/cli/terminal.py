import re
import sys

from termcolor import colored


def _sanitize_text(text: str) -> str:
    """Prepare text for printing, stripping ANSI codes for non-terminals."""
    # check if output is a terminal
    if sys.stdout.isatty():
        return text
    
    # strip ANSI color codes
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


def output(text: str, file=sys.stdout):
    """Print text, stripping formatting for non-terminals."""
    print(_sanitize_text(text), file=file)


def prompt(text: str = '', color: str | None = None) -> str:
    """Prompt user for input."""
    if color:
        text = colored(text, color)
    return input(_sanitize_text(text))
