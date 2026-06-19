import re

from .commands import COMMANDS, OPTIONS, ArgMap, Command, Flag, HelpCommand, ValueType, get_default_command
from .terminal import InputError


def _resolve_pending(pending_flags: list[type[Flag]], pending_tokens: list[str]) -> ArgMap:
    """
    Bind tokens to one flag and default values to all others.

    Disambiguation rules:
    1. Flags with required values take priority over optional ones.
    2. Flags which bind to int values are excluded if value is not int.
    3. If zero or multiple candidates remain, raise UserError.
    """
    none_flags = [f for f in pending_flags if f.value_type == ValueType.NONE]
    value_flags = [f for f in pending_flags if f.value_type != ValueType.NONE]

    consumer = None
    value = None

    # determine which flag binds to pending tokens
    if pending_tokens:
        required = [f for f in value_flags if f.required]
        optional = [f for f in value_flags if not f.required]

        # exclude INT flags for non-integer values
        if len(pending_tokens) > 1 or not pending_tokens[0].lstrip("-").isdigit():
            optional = [f for f in optional if f.value_type != ValueType.INT]

        # resolve consumer
        if len(required) == 1:
            consumer = required[0]
        elif len(required) > 1:
            raise InputError(f"ambiguous target for '{pending_tokens[0]}': " + ", ".join(f"-{f.char}" for f in required))
        elif len(optional) == 1:
            consumer = optional[0]
        elif len(optional) > 1:
            raise InputError(f"ambiguous target for '{pending_tokens[0]}': " + ", ".join(f"-{f.char}" for f in optional))
        else:
            raise InputError(
                ", ".join(f"-{f.char}" for f in pending_flags)
                + f" received invalid argument{('s' if len(pending_tokens) > 1 else '')}: "
                + ", ".join(f"'{t}'" for t in pending_tokens)
            )

        # extract value based on type
        if consumer.value_type == ValueType.TEXT:
            value = " ".join(pending_tokens)
        else:  # STR or INT
            if len(pending_tokens) > 1:
                raise InputError(
                    f"-{consumer.char} expects one token but got: " + ", ".join(f"'{t}'" for t in pending_tokens)
                )
            value = pending_tokens[0]
            if consumer.value_type == ValueType.INT:
                try:
                    value = int(value)
                except ValueError:
                    raise InputError(f"-{consumer.char} expects an integer but got: '{pending_tokens[0]}'") from None

    # resolve flag values
    args: ArgMap = {}
    for f in none_flags:
        args[f.char] = None
    for f in value_flags:
        if f == consumer:
            args[f.char] = value
        elif f.required:
            raise InputError(f"-{f.char} requires a value")
        else:
            args[f.char] = f.default
    return args


def parse(argv: list[str]) -> Command:
    """Parse command-line arguments into an executable command."""
    flag_lookup = {f.char: f for f in COMMANDS + OPTIONS}

    args: ArgMap = {}
    pending_flags: list[type[Flag]] = []
    pending_tokens: list[str] = []
    flag_parsing_enabled = True
    pos = 0

    while True:
        at_end = pos >= len(argv)
        token = argv[pos] if not at_end else None

        # handle -- sentinel
        if token == "--" and flag_parsing_enabled:
            flag_parsing_enabled = False
            pos += 1
            continue

        # resolve at boundary (new flag or end)
        is_flag = flag_parsing_enabled and token and bool(re.match(r"^-[a-z]+$", token))
        if is_flag or at_end:
            resolved = _resolve_pending(pending_flags, pending_tokens)

            duplicates = set(resolved.keys()) & set(args.keys())
            if duplicates:
                raise InputError(
                    f"duplicate flag{'' if len(duplicates) == 1 else 's'}: " + ", ".join(f"-{k}" for k in duplicates)
                )

            args.update(resolved)
            pending_flags, pending_tokens = [], []

        if at_end:
            break

        # accumulate flags
        if is_flag:
            for c in token[1:]:
                if c not in flag_lookup:
                    raise InputError(f"unknown flag: -{c}")
                pending_flags.append(flag_lookup[c])
            pos += 1
            continue

        # accumulate tokens (add default command if no pending flags)
        if not pending_flags:
            pending_flags.append(get_default_command())
        pending_tokens.append(token)
        pos += 1

    # validate commands
    valid_commands = {f.char for f in COMMANDS}
    commands = [c for c in args if c in valid_commands]
    if len(commands) > 1:
        raise InputError("multiple commands: " + ", ".join(f"-{c}" for c in commands))
    if not commands:
        if not args:
            return HelpCommand(args)
        raise InputError("no command specified")

    return flag_lookup[commands[0]](args)
