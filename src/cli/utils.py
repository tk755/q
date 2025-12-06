import re
import sys

from termcolor import colored


def use_color() -> bool:
    """Use colors if stdout is a terminal."""
    return sys.stdout.isatty()


def format_output(text: str) -> str:
    """Process text for terminal display."""
    # shorten links from web search responses
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text).strip()

    # convert two-plus newlines into only two
    text = re.sub(r'\n{2,}', '\n\n', text)

    # remove markdown formatting from code responses
    text = re.sub(r'^```.*?\n(.*)\n```$', r'\1', text, flags=re.DOTALL)

    if use_color():
        # convert code blocks into colored text
        text = re.sub(r'```(?:\w+\n?)?(.*?)```', lambda m: colored(m.group(1).strip(), 'cyan'), text, flags=re.DOTALL)

        # convert inline-code into colored text
        text = re.sub(r'`([^`]+)`', lambda m: colored(m.group(1), 'cyan'), text)

    return text
