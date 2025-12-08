import asyncio
import sys

from .commands import CommandError
from .terminal import qprint
from .parser import ParseError, parse
from .state import StateManager


def main():
    try:
        command, parsed_args = parse(sys.argv[1:])
        state = StateManager()
        asyncio.run(command.dispatch(parsed_args, state))
        state.save()

    except (ParseError, CommandError, ImportError) as e:
        qprint(str(e), color='red', file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    main()
