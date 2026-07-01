# Overview

`q` is an expressive, composable, provider-agnostic command-line interface for LLMs.

> I built `q` as a personal utility script before agentic coding tools like Claude Code released. It still excels at quick terminal prompts and shell script integration.

# Installation

Install using any pip-compatible package manager (e.g. `pip`, `pipx`, `uv`, etc.).

```bash
pipx install q-bot
```

Requires Python 3.12+.

# Syntax

`q` follows the Unix philosophy of composable, single-purpose utilities. Every character from `a` to `z` maps to a single command or option: a **command** performs a specific LLM task, an **option** modifies it. One command runs per invocation, alongside any number of options.

Flags are single characters and can be bundled, so `-sx` is `-s -x`. A command's prompt follows it directly and can be unquoted. `--` stops flag parsing so a prompt can contain leading dashes. With no command, a prompt reuses the last command in the session.

Run `q -h` for the full list of commands and options.

# Commands

## Shell (`-s`)

Generate a single shell command for the detected OS and shell. The model favors minimal, portable commands and is steered away from destructive ones (e.g. `rm -rf`, `dd`, `mkfs`, etc.). Without `-x`, the command is printed and copied to the clipboard.

```bash
$ q -s auto hide the dock          # on macOS
defaults write com.apple.dock autohide -bool true; killall Dock
```

`-x` automatically runs the generated command.

```bash
$ q -sx count commits on this branch
> git rev-list --count HEAD
95
```

With no prompt, `-s` reads your last shell command, re-runs it to capture the error, and fixes it.

```bash
$ git push
fatal: The current branch dev has no upstream branch.
$ q -sx
> git push --set-upstream origin dev
Branch 'dev' set up to track remote branch 'dev' from 'origin'.
```

<!-- TODO: Combine `-a` with `-s` and `-x` to continuously generate commands until the prompt is satisfied.

```bash
$ q -sxa get cuda version
> nvcc --version
bash: nvcc: command not found
> cat /usr/local/cuda/version.txt
cat: /usr/local/cuda/version.txt: No such file or directory
> nvidia-smi | grep "CUDA Version"
| NVIDIA-SMI 560.35.02    Driver Version: 560.94    CUDA Version: 12.6 |
``` -->

> [!IMPORTANT]
> Reading the last command requires a shell hook. Run `q -s` for instructions.

## Image (`-i`)

Generate an image.

```bash
$ q -i a cat floating in space -o space_cat.png
Image saved to space_cat.png
```

`-f` adds an image to edit or use as context. Keep prompting in the same session to refine previous images.

```bash
$ q -i remove the people in the background -f image.png
Image saved to q_remove_the_people_in_the_background.png
$ q -i crop above the waist -o headshot.png
Image saved to headshot.png
```

Image generation, editing, and refinement are all one command over a stateful image conversation. Each user-specified and assistant-generated image is fed back as context so later turns can refer to them.

> [!NOTE]
> Not all providers support images in assistant turns. In these cases, `q` spoofs the images as user turns, enabling multi-turn image editing for any provider that supports image generation.

> [!NOTE]
> Image generation is not supported by `anthropic`.

## Code (`-c`)

Generate an idiomatic code snippet and copy it to the clipboard.

```bash
$ q -c square every value in a dict
{k: v**2 for k, v in d.items()}
```

The default language is set in your [config](#configuration); `-l` overrides it.

```bash
$ q -c binary search -l rust -o search.rs
Response saved to search.rs
```

## Web (`-w`)

Search the web for real-time information with source attribution.

```bash
$ q -w nba champions
The New York Knicks are the 2026 NBA champions. (nba.com)
```

## Explain (`-e`)

Explain a command, snippet, or concept in a dense paragraph for an experienced reader.

```bash
$ q -e 'find . -type d -name .git -exec dirname {} \; | sort'
This walks the current directory tree, finds every .git directory, strips the trailing /.git to yield each repository root, and sorts the results lexicographically.
```

## Text (`-t`)

Generate raw text with no system prompt. Useful as a scripting primitive or a base for composition.

```bash
$ q -t write a sentence using only words that start with q
Quick quails quietly quench quivering quagmires.
```

## Help (`-h`)

With no prompt, `-h` prints usage information. With a prompt, `q` is able to answer questions about *itself* by using its own source code as context.

```bash
$ q -h is -- -k transient or persistent
-k is transient. It overrides the API key for a single command and is not saved to the .env file.
```

> [!NOTE]
> Prompting `-h` sends `q`'s source code as context; such queries consume a large number of input tokens.

# Sessions

Each terminal or script that runs `q` maintains an isolated **session**, which is a multi-turn history that persists across invocations, keyed to the parent shell process. Sessions are deleted automatically when that shell exits.

```bash
$ q -c merge two dictionaries x and y
$ q -t what is the time complexity          # same conversation
```

A session does not depend on the capability or provider, so either can be switched mid-conversation.

```bash
$ q -e explain photosynthesis -m anthropic
$ q -i draw a diagram -m openai             # new capability and provider
```

`-z` undoes the last `n` exchanges (default 1), and `-n` clears the history for a new conversation or a one-shot prompt.

# Model Selection

`q` defines three **tiers** (`low`, `med`, and `high`) for each provider and capability. A tier maps to a comparable model and tuned parameters on every provider, so the same tier is faster and cheaper at `low` and more capable at `high` regardless of which provider serves it.

Each command has a sensible default tier, which `-hv` displays. The default provider is set in your [config](#configuration). `-m` overrides the tier, provider, or specific model name.

```bash
$ q -c quicksort -m high                        # override tier, use default provider
$ q -c quicksort -m anthropic                   # override provider, use default tier
$ q -c quicksort -m anthropic:high              # override both provider and tier
$ q -c quicksort -m anthropic:claude-opus-4-8   # override provider and specify model
```

`-v` prints the resolved model, parameters, system prompt, and message history to stderr before the response.

# Input and Output Files

`-f` adds one or more files to any command. Text files are inserted as context; image files are sent as vision input. Both can be mixed in a single call.

```bash
$ q -e what does this module configure -f config.py
$ q -t compare these -f chart.png report.txt
```

`-o` writes the response or generated image to a path instead of stdout or the clipboard.

# Configuration

`q` stores state and configuration under `~/.q/`:
- **`.env`**: one API key per provider, prompted and saved the first time each provider is used.
- **`config.json`**: default `provider` (`openai`) and code language (`python`), created on first run.
- **`sessions/`**: one file per active session, reaped automatically when its shell exits.

`-k` overrides a provider's key for a single invocation without saving it to `.env`.

# Library Usage

`q` implements a small multi-provider library, built on two principles:
- **Single-capability clients:** clients have a static return type `T` and do not require mode switching or tool-selection.
- **Single interface and state model:** clients expose a uniform interface and state model so they can be swapped dynamically mid-conversation.

## Clients

A **client** is a wrapper around a provider's API for one capability. It stores conversation history as a list of portable `Message` objects and exposes two primary functions:
- `generate`: sends a prompt and returns the response, appending both to history.
- `batch_generate`: sends multiple prompts concurrently against the current history, leaving it unchanged.

The following built-in clients are provided for each provider:
| Client        | T       | Description                  | `openai` | `anthropic` | `google` |
| ------------- | ------- | ---------------------------- | :------: | :---------: | :------: |
| `TextClient`  | `str`   | text generation              | ✓        | ✓           | ✓        |
| `WebClient`   | `str`   | web-grounded text generation | ✓        | ✗           | ✓        |
| `ImageClient` | `bytes` | image generation             | ✓        | ✗           | ✓        |

## Dynamic Loading

Client classes are typically imported from their provider module (e.g. `q.openai`, `q.anthropic`, etc.), but they can also be loaded at runtime by provider and client name using the `load_client_class` utility.

```python
from q import load_client_class

client_class = load_client_class("openai", "ImageClient")
client = client_class(api_key, model, **model_args)
```

This is useful for building provider-agnostic tooling with minimal boilerplate, like the `q` CLI itself.

## Example

```python
from q import load_client_class

relay = [
    ("openai", openai_key, "gpt-5.4-mini"),
    ("anthropic", anthropic_key, "claude-sonnet-4-6"),
    ("google", google_key, "gemini-3.5-flash"),
]
messages = []
for provider, key, model in relay * 3:
    client = load_client_class(provider, "TextClient")(key, model, messages=messages)
    await client.generate("continue this story with one sentence", "You are a collaborative storyteller.")
    messages = client.messages
    print(f"{model}: {messages[-1].text}")
```
