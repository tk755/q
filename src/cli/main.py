import asyncio
import sys

from .parser import parse
from .terminal import UserError, qprint


def main():
    try:
        command = parse(sys.argv[1:])
        asyncio.run(command.execute())
    except (UserError, ImportError) as e:
        qprint(str(e), color="red", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
