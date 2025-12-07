import asyncio
import sys

from colorama import just_fix_windows_console
from termcolor import colored

from .commands import CommandError
from .terminal import output
from .parser import ParseError, parse
from .state import load_state, save_state


async def main():
    just_fix_windows_console()

    try:
        command, parsed_args = parse(sys.argv[1:])
        state = load_state()
        result = await command.dispatch(parsed_args, state)
        if result:
            output(result)
        save_state(state)

    except (ParseError, CommandError) as e:
        output(colored(str(e), 'red'), file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    asyncio.run(main())
