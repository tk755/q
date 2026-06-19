# Overview

`q` is a provider-agnostic, capability-driven LLM framework and command-line agent.

> I originally built this as a personal CLI tool before Claude Code existed. I still find it more useful for quick shell interactions and running multi-model experiments.

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

# Library Usage

The `q` library is built on two principles:

**Clients are single-capability.** Each client does one thing (e.g. text generation, image generation, web search, etc.) and has a static return type. No mode switching or tool selection logic is necessary.

**Agents are provider- and capability-agnostic.** Every agent accepts any client and inherits its return type, regardless of what the underlying client does or which provider it calls.

## Clients

A **client** wraps a provider's API for one capability.

Clients extend `Client[T]` and require an API key and model name, along with any model-specific overrides:

```python
Client[T](api_key: str, model: str, **model_args)
Client[T].generate(messages: list[Message]) -> T
```

A number of built-in clients are provided for various providers and capabilities:

| Client        | T       | Description                  | `openai` | `anthropic` |
| ------------- | ------- | ---------------------------- | :------: | :---------: |
| `TextClient`  | `str`   | text generation              | ✓        | ✓           |
| `WebClient`   | `str`   | web-grounded text generation | ✓        | ✗           |
| `ImageClient` | `bytes` | image generation             | ✓        | ✗           |

Clients can be instantiated directly from their provider module:

```python
from q.providers.openai import WebClient

client = WebClient(api_key, model="gpt-5.4-mini", reasoning={"effort": "high"})
```

Clients can also be dynamically loaded by specifying the provider and capability:

```python
from q.providers import load_client_class

client_class = load_client_class('openai', 'ImageClient')
client = client_class(api_key, model, **model_args)
```

## Agents

An **agent** manages conversation state and delegates generation to a client. Two built-in agents are provided:

`ChatAgent[T]` maintains a message history and prepends an optional system prompt:

```python
ChatAgent[T](client: Client[T], system: str | None = None)
ChatAgent[T].prompt(text: str) -> T
```

`BatchAgent[T]` processes multiple inputs concurrently against a shared system prompt, with no conversation history:

```python
BatchAgent[T](client: Client[T], system: str | None = None)
BatchAgent[T].batch_prompt(text_list: list[str], n_threads: int = 8) -> list[T]
```

## Example

This lightweight architecture enables full functionality with minimal code.

```python
from q.providers.openai import ImageClient
from q.agents import ChatAgent

client = ImageClient(api_key, "gpt-image-1", quality="high")
agent = ChatAgent(client)
image_bytes = await agent.prompt("a cat in space")
Path("cat.png").write_bytes(image_bytes)
```