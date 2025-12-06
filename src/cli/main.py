import sys

from colorama import just_fix_windows_console
from termcolor import cprint

from .commands import CommandError
from .parser import ParseError, parse
from .state import load_state, save_state
from .utils import use_color


def main():
    if use_color():
        just_fix_windows_console()

    try:
        command, parsed_args = parse(sys.argv[1:])
        state = load_state()
        result = command.dispatch(parsed_args, state)
        if result:
            print(result)
        save_state(state)

    except (ParseError, CommandError) as e:
        if use_color():
            cprint(str(e), 'red', file=sys.stderr)
        else:
            print(str(e), file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    main()
