import asyncio
import sys

from .parser import QError, parse
from .terminal import qprint


def main():
    try:
        command = parse(sys.argv[1:])
        asyncio.run(command.execute())
    except (QError, ImportError) as e:
        qprint(str(e), color="red", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
