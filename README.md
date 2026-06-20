# Overview

`q` is a provider-agnostic command-line agent and LLM framework.

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

| Flag | Name         | Arg     | Description                       | Type    |
| ---- | ------------ | ------- | --------------------------------- | ------: |
| `-a` | agent        |         | *[reserved for future use]*       | Command |
| `-b` | batch        |         | *[reserved for future use]*       | Command |
| `-c` | code         | str     | generate code                     | Command |
| `-d` | directory    | - / str | add a directory to context        | Option  |
| `-e` | explain      | - / str | explain code or text              | Command |
| `-f` | file         | str     | read input from file              | Option  |
| `-g` |              |         |                                   |         |
| `-h` | help         | - / str | help message / agent              | Command |
| `-i` | image        | str     | generate/edit an image            | Command |
| `-j` | json         | -       | output as JSON                    | Option  |
| `-k` | api key      | str     | override API key                  | Option  |
| `-l` | code lang    | str     | override code generation language | Option  |
| `-m` | model        | str     | override model/provider           | Option  |
| `-n` | new session  | -       | clear the session history         | Option  |
| `-o` | output       | str     | output file                       | Option  |
| `-p` |              |         |                                   |         |
| `-q` |              |         |                                   |         |
| `-r` | rag          | - / str | *[reserved for future use]*       | Command |
| `-s` | shell        | - / str | generate a shell command          | Command |
| `-t` | text         | str     | generate text                     | Command |
| `-u` | user command | str     | *[reserved for future use]*       | Command |
| `-v` | verbose      | -       | debug logging                     | Option  |
| `-w` | web          | str     | search the web                    | Command |
| `-x` | execute      | -       | execute a shell command           | Option  |
| `-y` |              |         |                                   |         |
| `-z` | undo         | - / int | undo exchanges (default 1)        | Option  |

## Sessions

Each terminal or script that runs `q` maintains an isolated **session** that persists conversation history across calls. Use `-n` to clear the session history for a new conversation or one-shot prompt. Sessions are automatically deleted when the parent shell process exits.

# Library Usage

The `q` library is built on two principles:

**Clients are single-capability.** Each client does one thing (e.g. text generation, image generation, web search, etc.) and has a static return type. No mode switching or tool selection logic is necessary.

**Agents are provider- and capability-agnostic.** Every agent accepts any client and inherits its return type, regardless of what the underlying client does or which provider it calls.

## Clients

A **client** wraps a provider's API for one capability.

Clients extend `Client[T]` and are instantiated with an API key, model name, and optionally provider- and model-specific argument overrides. All clients expose the same `generate` method which returns a value of type `T`:

```python
Client[T](api_key: str, model: str, **model_args)
Client[T].generate(messages: list[Message]) -> T
```

A number of built-in clients with sensible defaults are provided for the following providers and capabilities:

| Client        | T       | Description                  | `openai` | `anthropic` |
| ------------- | ------- | ---------------------------- | :------: | :---------: |
| `TextClient`  | `str`   | text generation              | ✓        | ✓           |
| `WebClient`   | `str`   | web-grounded text generation | ✓        | ✗           |
| `ImageClient` | `bytes` | image generation             | ✓        | ✗           |

### Dynamic Loading

Client classes are typically imported from their provider module:

```python
from q.providers.openai import ImageClient

client = ImageClient(api_key, model, **model_args)
```

They can also be dynamically loaded at runtime by specifying a provider and capability using the `load_client_class` utility:

```python
from q.providers import load_client_class

client_class = load_client_class('openai', 'ImageClient')
client = client_class(api_key, model, **model_args)
```

## Agents

An **agent** manages conversation state and delegates generation to a client.

`ChatAgent[T]` maintains a message history and prepends an optional system prompt:

```python
ChatAgent[T](client: Client[T], system: str | None = None)
ChatAgent[T].prompt(text: str) -> T
```

`BatchAgent[T]` processes multiple inputs concurrently using a shared system prompt, with no conversation history:

```python
BatchAgent[T](client: Client[T], system: str | None = None)
BatchAgent[T].batch_prompt(text_list: list[str], n_threads: int = 8) -> list[T]
```

<!-- ## Examples

This design enables full LLM functionality with minimal code.

**Example 1:** Generate an image via OpenAI

```python
from q.providers.openai import ImageClient
from q.agents import ChatAgent

client = ImageClient(api_key, "gpt-image-2", quality="high")
agent = ChatAgent(client)
image_bytes = await agent.prompt("a cat in space")
Path("cat.png").write_bytes(image_bytes)
```

**Example 2:** Generate batch text via Anthropic

```python
from q.providers.anthropic import TextClient
from q.agents import BatchAgent

client = TextClient(api_key, "claude-opus-4-8")
agent = BatchAgent(client, system="Identify the language of the text.")
inputs = ["How are you?", "¿Cómo estás?", "Comment ça va?"]
langs = await agent.batch_prompt(inputs)
```

**Example 3:** Multi-model orchestration

```python
from q.providers import load_client_class
from q.agents import ChatAgent

client1 = load_client_class('openai', 'TextClient')(oai_key, "gpt-5-5")
client2 = load_client_class('anthropic', 'TextClient')(anthropic_key, "claude-opus-4-8")

system = "You are an AI speaking with another AI. Engage in a discussion about the future of AI."

agent1 = ChatAgent(client1, system=system)
agent2 = ChatAgent(client2, system=system)

text = "What are your thoughts on the future of AI?"

for _ in range(5):
    text = await agent1.prompt(text)
    print("agent1:", text)
    text = await agent2.prompt(text)
    print("agent2:", text)
``` -->
