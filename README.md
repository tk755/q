# Overview

`q` is an expressive [command-line utility](#command-line-usage) and provider-agnostic [library](#library-usage) for LLMs.

> I built `q` as a personal utility script before the emergence of agentic coding tools like Claude Code. It has since been optimized for its particular niche: quick terminal interaction, shell script integration, and multi-model experimentation.

# Installation

Install using any pip-compatible package manager (e.g. `pip`, `pipx`, `uv`, etc.):

```bash
pipx install q-bot
```

Requires Python 3.12+.

# Command-Line Usage

`q` follows the Unix philosophy of composable, single-purpose utilities.

Every character from `a` to `z` maps to a command or option. A **command** performs a specific LLM task, while an **option** modifies a command's behavior. Together, they can express a wide variety of LLM operations precisely and concisely.

Run `q -h` or see the [Flag Reference](#flag-reference) below for a complete list of commands and options.

## Examples

### Shell Command Generation and Execution

Use `-s` to generate shell commands and copy them to the clipboard. `q` automatically detects the operating system and shell to generate compatible commands:

```bash
$ q -s auto hide the dock # on macOS
defaults write com.apple.dock autohide -bool true; killall Dock
```

Use `-x` to automatically execute the generated command:

```bash
$ q -sx count number of commits
> git rev-list --count HEAD
95
```

With no prompt, `-s` re-runs the last shell command, reads the error, and fixes it:

```bash
$ git push
fatal: The current branch dev has no upstream branch.
$ q -sx
> git push --set-upstream origin dev
Branch 'dev' set up to track remote branch 'dev' from 'origin'.
```

> [!IMPORTANT]
> This requires a small shell hook to expose your previous command to `q`. Run `q -s` for more instructions.

### Code Generation

Use `-c` to generate idiomatic code snippets and copy them to the clipboard. The default language is set in the [config](#configuration):

```bash
$ q -c square all keys in a dict
squared_keys = {k**2: v for k, v in d.items()}
```

Use `-l` to specify the language, and `-o` to write the output to a file:

```bash
$ q -c binary search -l rust -o search.rs
Response saved to search.rs
```

<!-- Use `-f` to provide an input file as context:

```bash
$ q -c add docstrings to all functions -f lib.py -o lib_doc.py
Response saved to lib_doc.py
``` -->

### Image <!--Editing and -->Generation

Use `-i` to generate an image:

```bash
$ q -i a cat in space
Image saved to q_a_cat_in_space.png
```

### Web Search

Use `-w` to search the web for real-time information with source attribution:

```bash
$ q -w nba champions
The New York Knicks are the 2026 NBA champions. (nba.com)
```

### Explanation

Use `-e` to get an explanation of any command, snippet, or concept:

```bash
$ q -e 'find . -type d -name .git -exec dirname {} \; | sort'
This walks the current directory tree, finds every .git directory, strips the trailing /.git to yield the repository root path, and then sorts the results lexicographically.
```

### Text Generation

Use `-t` to generate text without a system prompt:

```bash
$ q -t write a sentence with only words starting with q
Quick quails quietly quench quivering quagmires.
```

### Help Agent

Use `-h` to pass a question to the built-in help agent which answers from `q`'s own source code:

```bash
$ q -h where are api keys stored
API keys are stored in ~/.q/.env
```

<!-- ### Batch Commands

Use `-b` to run a command on each line of a file:

```bash
$ q -sx "install this package: " -b packages.txt
``` -->

## Sessions

Each terminal or script that runs `q` maintains an isolated **session** that persists multi-turn conversation history across calls. Sessions are automatically deleted when the parent shell process exits.

Invoking `q` without a command reuses the previous one in the session. Use `-n` to clear the session history for a new conversation or one-shot prompt. Use `-z` to undo previous exchanges.

## Model Selection

`q` defines four capability **tiers** per provider: `low`, `med`, `high`, and `max`. Each maps to a comparable model and parameters on every provider, with lower tiers faster and cheaper, and higher tiers more capable. Tiers abstract away model and parameter selection, making it easy to switch providers or scale capability up and down.

Each command defines a default tier, and the default provider is set in the [config](#configuration). Use `-m` to override the default model selection by tier, provider, or specific model name:

```bash
$ q -c quicksort -m max                         # override tier, use default provider
$ q -c quicksort -m anthropic                   # override provider, use default tier
$ q -c quicksort -m anthropic:max               # override both provider and tier
$ q -c quicksort -m anthropic:claude-opus-4-8   # override provider and specify model
```

Use `-v` to inspect the resolved provider, model, and parameters.

## Configuration

`q` maintains persistent state and configuration files in `~/.q/`:
- **`~/.q/.env`** - One API key per provider, prompted the first time each provider is called.
- **`~/.q/config.json`** - Default `provider` (`openai`) and `code_lang` (`python`), created automatically on first run.
- **`~/.q/sessions/`** - One `<pid>.json` file per active session, deleted automatically when stale.

Use `-k` to override the default API key for a single invocation, useful for switching accounts or testing a key without persisting it.

## Flag Reference

| Flag | Name         | Arg     | Description                       | Type    | Tier | WIP |
| ---- | ------------ | ------- | --------------------------------- | --------| ---- | :--:|
| `-a` | agent        | ?       | *[reserved for future use]*       | Command | ?    | ✗   |
| `-b` | batch        | ?       | *[reserved for future use]*       |         | ?    | ✗   |
| `-c` | code         | str     | generate code                     | Command | high |     |
| `-d` | directory    | - / str | add directory to context          | Option  | -    | ✗   |
| `-e` | explain      | - / str | explain code or text              | Command | high |     |
| `-f` | file         | str     | add file contents to context      | Option  | -    | ✗   |
| `-g` |              |         |                                   |         |      |     |
| `-h` | help         | - / str | help message / agent              | Command | low  |     |
| `-i` | image        | str     | generate/edit an image            | Command | med  |     |
| `-j` | json         | -       | output in JSON format             | Option  | -    | ✗   |
| `-k` | api key      | str     | override API key                  | Option  | -    |     |
| `-l` | code lang    | str     | override code generation language | Option  | -    |     |
| `-m` | model        | str     | override model/provider           | Option  | -    |     |
| `-n` | new session  | -       | clear the session history         | Option  | -    |     |
| `-o` | output path  | str     | write output to a file            | Option  | -    |     |
| `-p` |              |         |                                   |         |      |     |
| `-q` |              |         |                                   |         |      |     |
| `-r` | rag          | - / str | retrieval augmented generation    | Command | ?    | ✗   |
| `-s` | shell        | - / str | generate a shell command          | Command | med  |     |
| `-t` | text         | str     | generate text                     | Command | med  |     |
| `-u` | user command | str     | *[reserved for future use]*       | Command | ?    | ✗   |
| `-v` | verbose      | -       | debug logging                     | Option  | -    |     |
| `-w` | web          | str     | search the web                    | Command | low  |     |
| `-x` | execute      | -       | execute shell command             | Option  | -    |     |
| `-y` |              |         |                                   |         |      |     |
| `-z` | undo         | - / int | undo exchanges (default: 1)       | Option  | -    |     |

# Library Usage

The `q` library is built on two principles:
- **Clients are single-capability.** Each client does one thing (e.g. text generation, image generation, web search, etc.) and has a static return type. No mode switching or tool selection logic is necessary.
- **Agents are provider- and capability-agnostic.** Every agent accepts any client and inherits its return type, regardless of what the underlying client does or which provider it calls.

This leads to a simple, explicit architecture that requires little boilerplate to use or extend.

## Clients

A **client** is a wrapper around a provider's API for one capability.

Clients extend `Client[T]` and are instantiated with an API key, model name, and optionally provider- and model-specific argument overrides. All clients expose a `generate` method which invokes the LLM, retries transient failures, and returns a value of type `T`:

```python
Client[T](api_key: str, model: str, **model_args)
async Client[T].generate(messages: list[Message]) -> T
```

The following built-in clients are provided for each provider and capability:

| Client        | T       | Description                  | `openai` | `anthropic` |
| ------------- | ------- | ---------------------------- | :------: | :---------: |
| `TextClient`  | `str`   | text generation              | ✓        | ✓           |
| `WebClient`   | `str`   | web-grounded text generation | ✓        | ✗           |
| `ImageClient` | `bytes` | image generation             | ✓        | ✗           |

### Dynamic Loading

Client classes are typically imported from their provider module, but can also be dynamically loaded at runtime by specifying a provider and capability using the `load_client_class` utility:

```python
from q.providers import load_client_class

client_class = load_client_class('openai', 'ImageClient')
client = client_class(api_key, model, **model_args)
```

This is useful for building multi-provider systems or provider-agnostic tooling.

## Agents

An **agent** is a wrapper around a client that manages messages and provides a consistent interface for prompting.

`ChatAgent[T]` is a conversational agent with persistent message history.

```python
ChatAgent[T](client: Client[T], system: str | None = None, messages: list[Message] | None = None)
async ChatAgent[T].prompt(text: str) -> T
ChatAgent[T].drop_exchanges(n: int = 1) -> None
```

`BatchAgent[T]` processes multiple inputs in parallel without message history.

```python
BatchAgent[T](client: Client[T], system: str | None = None)
async BatchAgent[T].batch_prompt(text_list: list[str], n_threads: int = 8) -> list[T]
```

## Examples

### Basic Usage

```python
from pathlib import Path
from q.providers.openai import ImageClient
from q.agents import ChatAgent

client = ImageClient(api_key, "gpt-image-2", quality="high")
agent = ChatAgent(client)
image_bytes = await agent.prompt("a cat in space")
Path("cat.png").write_bytes(image_bytes)
```

### Batch Processing

```python
from q.providers.anthropic import TextClient
from q.agents import BatchAgent

client = TextClient(api_key, "claude-opus-4-8")
agent = BatchAgent(client, system="Identify the language of the text.")
inputs = ["How are you?", "¿Cómo estás?", "Comment ça va?"]
langs = await agent.batch_prompt(inputs)
```

### Multi-Agent Orchestration

```python
from q.providers import load_client_class
from q.agents import ChatAgent

client1 = load_client_class('openai', 'TextClient')(openai_key, "gpt-5.5")
client2 = load_client_class('anthropic', 'TextClient')(anthropic_key, "claude-opus-4-8")

system = "You are an AI speaking with another AI. Discuss the future of AI."
agent1 = ChatAgent(client1, system=system)
agent2 = ChatAgent(client2, system=system)

text = "What are your thoughts on the future of AI?"
for _ in range(5):
    text = await agent1.prompt(text)
    print("agent1:", text)
    text = await agent2.prompt(text)
    print("agent2:", text)
```
