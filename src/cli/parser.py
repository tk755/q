import os
import re
from dataclasses import dataclass
from enum import Enum, auto


Value = str | int | None


class ParseError(Exception):
    pass


class ArgType(Enum):
    NONE = auto()  # no argument (boolean flag)
    TEXT = auto()  # contiguous multi-token text
    STR = auto()   # single string token
    INT = auto()   # single integer token


@dataclass
class Flag:
    char: str
    desc: str
    arg_type: ArgType = ArgType.NONE
    required: bool = False
    default: Value = None


DEFAULT_CMD = "t"

COMMANDS: list[Flag] = [
    Flag("c", "generate code", ArgType.TEXT, required=True),
    Flag("e", "explain code or text", ArgType.TEXT),
    Flag("h", "show help message"),
    Flag("i", "generate/edit image", ArgType.TEXT, required=True),
    Flag("l", "list or load session", ArgType.INT),
    Flag("q", "generate a q command", ArgType.TEXT, required=True),
    Flag("r", "retrieval augmented generation", ArgType.TEXT),
    Flag("s", "generate shell command", ArgType.TEXT),
    Flag("t", "pure text prompt", ArgType.TEXT, required=True),
    Flag("u", "run user command", ArgType.STR, required=True),
    Flag("w", "web search", ArgType.TEXT, required=True),
]

OPTIONS: list[Flag] = [
    Flag("d", "add directory to context", ArgType.STR, default=os.getcwd()),
    Flag("f", "read input from file", ArgType.STR, required=True),
    Flag("j", "output as JSON"),
    Flag("m", "override model", ArgType.STR, required=True),
    Flag("o", "write output to file", ArgType.STR, required=True),
    Flag("v", "debug logging"),
    Flag("x", "execute shell command"),
    Flag("z", "undo n exchanges", ArgType.INT, default=1),
]

FLAG_LOOKUP: dict[str, Flag] = {f.char: f for f in COMMANDS + OPTIONS}


def _resolve_flags(acc_flags: list[Flag], acc_tokens: list[str]) -> dict[str, Value]:
    """
    Assign tokens to one flag and default values to all others.
    
    Token assignment disambiguation rules:
    1. Flags with required args take priority over flags with optional args.
    2. Flags with int args are excluded if tokens cannot cast to int.
    3. If zero or multiple candidate flags remain, raise ParseError.
    """
    none_flags = [f for f in acc_flags if f.arg_type == ArgType.NONE]
    arg_flags = [f for f in acc_flags if f.arg_type != ArgType.NONE]

    consumer_flag = None
    value = None
    
    # determine which flag consumes accumulated tokens
    if acc_tokens:
        required_flags = [f for f in arg_flags if f.required]
        optional_flags = [f for f in arg_flags if not f.required]

        # exclude INT flags for non-integer tokens
        if len(acc_tokens) > 1 or not acc_tokens[0].lstrip('-').isdigit():
            optional_flags = [f for f in optional_flags if f.arg_type != ArgType.INT]

        # resolve consumer flag
        if len(required_flags) == 1:
            consumer_flag = required_flags[0]
        elif len(required_flags) > 1:
            raise ParseError(f"ambiguous target for '{acc_tokens[0]}': " + ", ".join(f"-{f.char}" for f in required_flags))
        elif len(optional_flags) == 1:
            consumer_flag = optional_flags[0]
        elif len(optional_flags) > 1:
            raise ParseError(f"ambiguous target for '{acc_tokens[0]}': " + ", ".join(f"-{f.char}" for f in optional_flags))
        else:
            raise ParseError(f"unexpected argument{'' if len(acc_tokens) == 1 else 's'}: " + ", ".join(f"'{t}'" for t in acc_tokens))

        # extract value based on arg type
        if consumer_flag.arg_type == ArgType.TEXT:
            value = ' '.join(acc_tokens)
        else:  # STR or INT
            if len(acc_tokens) > 1:
                raise ParseError(f"-{consumer_flag.char} expects one argument but got: " + ", ".join(f"'{t}'" for t in acc_tokens))
            value = acc_tokens[0]
            if consumer_flag.arg_type == ArgType.INT:
                try:
                    value = int(value)
                except ValueError:
                    raise ParseError(f"-{consumer_flag.char} expects an integer but got: '{acc_tokens[0]}'") from None

    # resolve flag values
    flags: dict[str, Value] = {}
    for f in none_flags:
        flags[f.char] = None
    for f in arg_flags:
        if f == consumer_flag:
            flags[f.char] = value
        elif f.required:
            raise ParseError(f"-{f.char} expects an argument but got none")
        else:
            flags[f.char] = f.default
    return flags


def parse(args: list[str]) -> tuple[str | None, dict[str, Value]]:
    """Parse command-line arguments into a (cmd, flags) tuple."""
    flags: dict[str, Value] = {}
    acc_flags: list[Flag] = []
    acc_tokens: list[str] = []
    flag_parsing_enabled = True
    pos = 0

    while True:
        at_end = pos >= len(args)
        token = args[pos] if not at_end else None

        # handle -- sentinel
        if token == '--' and flag_parsing_enabled:
            flag_parsing_enabled = False
            pos += 1
            continue

        # resolve pending flags at boundary (i.e. new flags or end)
        is_flag = flag_parsing_enabled and token and bool(re.match(r'^-[a-z]+$', token))
        if is_flag or at_end:
            resolved_flags = _resolve_flags(acc_flags, acc_tokens)
            
            dup_flags = set(resolved_flags.keys()) & set(flags.keys())
            if dup_flags:
                raise ParseError(f"duplicate flag{'' if len(dup_flags) == 1 else 's'}: " + ", ".join(f"-{k}" for k in dup_flags))
            
            flags.update(resolved_flags)
            acc_flags, acc_tokens = [], []

        if at_end:
            break

        # accumulate flags
        if is_flag:
            chars = token[1:]
            for c in chars:
                if c not in FLAG_LOOKUP:
                    raise ParseError(f"unknown flag: -{c}")
                acc_flags.append(FLAG_LOOKUP[c])
            pos += 1
            continue

        # accumulate token (add default command if no pending flags)
        if not acc_flags:
            acc_flags.append(FLAG_LOOKUP[DEFAULT_CMD])
        acc_tokens.append(token)
        pos += 1

    # validate commands
    all_commands = [f.char for f in COMMANDS]
    commands = [c for c in flags if c in all_commands]
    if len(commands) > 1:
        raise ParseError(f"multiple commands: " + ", ".join(f"-{c}" for c in commands))
    cmd = commands[0] if commands else None

    return cmd, flags
