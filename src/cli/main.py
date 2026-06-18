import asyncio
import os
import sys
from pathlib import Path

from .parser import parse
from .terminal import UserError, is_terminal, qprint


def main():
    # suppress stderr when piped
    if not is_terminal():
        sys.stderr = Path(os.devnull).open("w") # noqa: SIM115

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
