import re

from .commands import FLAG_MAP, Command, Flag, FlagValue, HelpCommand, ValueType, get_default_command
from .terminal import InputError


def _resolve_pending(pending_flags: list[type[Flag]], pending_tokens: list[str]) -> dict[type[Flag], FlagValue]:
    """
    Bind tokens to one flag and default values to all others.

    Disambiguation rules:
    1. Flags with required values take priority over optional ones.
    2. Flags which bind to int values are excluded if value is not int.
    3. If zero or multiple candidates remain, raise UserError.
    """
    none_flags = [flag for flag in pending_flags if flag.value_type == ValueType.NONE]
    value_flags = [flag for flag in pending_flags if flag.value_type != ValueType.NONE]

    consumer: type[Flag] | None = None
    value: FlagValue = None

    # determine which flag binds to pending tokens
    if pending_tokens:
        required_flags = [flag for flag in value_flags if flag.required]
        optional_flags = [flag for flag in value_flags if not flag.required]

        # exclude INT flags for non-integer values
        if len(pending_tokens) > 1 or not pending_tokens[0].lstrip("-").isdigit():
            optional_flags = [flag for flag in optional_flags if flag.value_type != ValueType.INT]

        # resolve consumer
        if len(required_flags) == 1:
            consumer = required_flags[0]
        elif len(required_flags) > 1:
            raise InputError(f"ambiguous target for '{pending_tokens[0]}': " + ", ".join(f"-{flag.char}" for flag in required_flags))
        elif len(optional_flags) == 1:
            consumer = optional_flags[0]
        elif len(optional_flags) > 1:
            raise InputError(f"ambiguous target for '{pending_tokens[0]}': " + ", ".join(f"-{flag.char}" for flag in optional_flags))
        else:
            raise InputError(
                ", ".join(f"-{flag.char}" for flag in pending_flags)
                + f" received invalid argument{('s' if len(pending_tokens) > 1 else '')}: "
                + ", ".join(f"'{token}'" for token in pending_tokens)
            )

        # extract value based on type
        if consumer.value_type == ValueType.TEXT:
            value = " ".join(pending_tokens)
        else:  # STR or INT
            if len(pending_tokens) > 1:
                raise InputError(
                    f"-{consumer.char} expects one token but got: " + ", ".join(f"'{token}'" for token in pending_tokens)
                )
            value = pending_tokens[0]
            if consumer.value_type == ValueType.INT:
                try:
                    value = int(value)
                except ValueError:
                    raise InputError(f"-{consumer.char} expects an integer but got: '{pending_tokens[0]}'") from None

    # bind values to flags
    bindings: dict[type[Flag], FlagValue] = {}
    for flag in none_flags:
        bindings[flag] = None
    for flag in value_flags:
        if flag == consumer:
            bindings[flag] = value
        elif flag.required:
            raise InputError(f"-{flag.char} requires a value")
        else:
            bindings[flag] = flag.default
    return bindings


def parse(argv: list[str]) -> Command:
    """Parse command-line arguments into an executable command."""
    bindings: dict[type[Flag], FlagValue] = {}
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
            resolved_bindings = _resolve_pending(pending_flags, pending_tokens)

            duplicate_flags = set(resolved_bindings) & set(bindings)
            if duplicate_flags:
                raise InputError(
                    f"duplicate flag{'' if len(duplicate_flags) == 1 else 's'}: "
                    + ", ".join(f"-{flag.char}" for flag in duplicate_flags)
                )

            bindings.update(resolved_bindings)
            pending_flags, pending_tokens = [], []

        if at_end:
            break

        # accumulate flags
        if is_flag:
            for char in token[1:]:
                if char not in FLAG_MAP:
                    raise InputError(f"unknown flag: -{char}")
                pending_flags.append(FLAG_MAP[char])
            pos += 1
            continue

        # accumulate tokens (add default command if no pending flags)
        if not pending_flags:
            pending_flags.append(get_default_command())
        pending_tokens.append(token)
        pos += 1

    # validate command
    command_flags = [flag for flag in bindings if issubclass(flag, Command)]
    if len(command_flags) > 1:
        raise InputError("multiple commands: " + ", ".join(f"-{flag.char}" for flag in command_flags))
    if not command_flags:
        if not bindings:  # blank input
            return HelpCommand(None, {})
        raise InputError("no command specified")

    # instantiate command
    command_flag = command_flags[0]
    command_value = bindings[command_flag]
    opts = {flag: value for flag, value in bindings.items() if flag is not command_flag}
    return command_flag(command_value, opts)
