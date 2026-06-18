# Overview

`q` is a lightweight, flexible, multi-provider LLM-agent framework for the terminal. 

I built this before Claude Code ever existed, and it remains useful to me for quick CLI interactions or prototyping multi-agent experiments. However, for most complex coding tasks, Claude Code is unquestionably superior.

# Installation

Install using any pip-compatible package manager (e.g. `pip`, `pipx`, `uv`, etc.):

```bash
pipx install q-bot
```

Requires Python 3.12+.

# CLI Usage

`q` uses a simple paradigm where each character from a-z is mapped to a single flag representing a command or option. This enables concise combinations of flags to achieve complex behavior.

## Flag Reference

| Flag | Name         | Arg     | Description                    | Type    |
| ---- | ------------ | ------- | ------------------------------ | ------: |
| `-a` | agent        |         | *[reserved for future use]*    | Command |
| `-b` | batch        |         | *[reserved for future use]*    |         |
| `-c` | code         | str     | generate code                  | Command |
| `-d` | directory    | - / str | add a directory to context     | Option  |
| `-e` | explain      | - / str | explain code or text           | Command |
| `-f` | file         | str     | read input from file           | Option  |
| `-g` |              |         |                                |         |
| `-h` | help         | - / str | help message / help agent      | Command |
| `-i` | image        | str     | generate/edit an image         | Command |
| `-j` | json         | -       | output as JSON                 | Option  |
| `-k` | api key      | str     | *[reserved for future use]*    | Option  |
| `-l` | load         | - / int | list all / load session by id  | Command |
| `-m` | model        | str     | set model and/or provider      | Option  |
| `-n` |              |         |                                |         |
| `-o` | output       | str     | output file                    | Option  |
| `-p` |              |         |                                |         |
| `-q` |              |         |                                |         |
| `-r` | rag          | - / str | *[reserved for future use]*    | Command |
| `-s` | shell        | - / str | generate a shell command       | Command |
| `-t` | text         | str     | generate text                  | Command |
| `-u` | user command | str     | *[reserved for future use]*    | Command |
| `-v` | verbose      | -       | debug logging                  | Option  |
| `-w` | web search   | str     | search the web                 | Command |
| `-x` | execute      | -       | execute a shell command        | Option  |
| `-y` |              |         |                                |         |
| `-z` | undo         | - / int | undo exchanges (default 1)     | Option  |

<!-- [TODO]

# Library Usage

`q` follows a highly modular and provider-agnostic capability-driven design. -->
