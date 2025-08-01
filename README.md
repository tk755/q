# Overview
`q` is an LLM-powered programming copilot from the comfort of your command line. It can generate code snippets, shell commands, technical explanations, web searches, and images. With multi-turn conversations, it can build, debug, and refine complex solutions iteratively. It even saves generated code snippets and shell commands to your clipboard, so you can paste them wherever needed.

Currently `q` uses the OpenAI API, but support for other LLM providers is planned in the future.

## Why Not Claude Code?

I built `q` before Claude Code existed. Now I use both. `q` is still cheaper and faster for quick, non-contextual queries. Claude Code excels at everything else.

# Installation

Install using `pipx` (recommended):

```bash
pipx install q-bot
```

Or `pip`:

```bash
pip install q-bot
```

Requires Python 3.8+.

# Usage

> **🔑 API Key Required**  
> The first time you run `q`, you will be prompted for an OpenAI API key which you can create [here](https://platform.openai.com/api-keys).

The command syntax is `q [command] TEXT [options]`. `q` accepts at most one command, along with any number of options. Any arguments between the command and options are treated as input text.

`q` saves generated code snippets and shell commands to your clipboard so you can paste them wherever needed. This generally does not work on headless environments (e.g. VMs and Docker containers); see [here](https://pyperclip.readthedocs.io/en/latest/index.html#not-implemented-error) for troubleshooting on other systems.

For a full list of commands and options, run `q -h`.

## Commands

Each command sends a custom prompt to the OpenAI API and returns the parsed response.

### Generate Code

Use the `-c` or `--code` command to generate code snippets:

```
$ q -c copy user input to clipboard
import pyperclip

user_input = input("Enter text to copy to clipboard: ")
pyperclip.copy(user_input)
```

By default this generates Python code, but you can specify a different programming language in the prompt itself:

```
$ q -c copy user input to clipboard in rust
use std::io::{self, Write};
use clipboard::{ClipboardContext, ClipboardProvider};

fn main() {
    let mut input = String::new();
    print!("Enter text to copy to clipboard: ");
    io::stdout().flush().unwrap();
    io::stdin().read_line(&mut input).unwrap();

    let mut ctx: ClipboardContext = ClipboardProvider::new().unwrap();
    ctx.set_contents(input.trim().to_string()).unwrap();
}
```

You can redirect the output to a file and run it instantly:

```
$ q -c fib function w main function > fib.py && python3 fib.py
Enter a number: 10
Fibonacci number at position 10 is 55
```

### Generate Shell Commands

Use the `-s` or `--shell` command to generate shell commands:

```
$ q -s add README.md to prev commit and push changes
git add README.md && git commit --amend --no-edit && git push --force-with-lease
```

By default this generates Bash commands for a Debian system, but you can specify a different shell or OS in the prompt itself:

```
$ q -s auto hide the dock on macos
defaults write com.apple.dock autohide -bool true; killall Dock
```

You can pipe the output to the shell interpreter to run it instantly:

```
$ q -s count line numbers in fib.py | bash
12 fib.py
```

### Explain

Use the `-e` or `--explain` command to generate a concise explanation for code snippets or shell commands:

```
$ q -e 'print(os.getcwd())'
`print(os.getcwd())` outputs the current working directory of the Python process by calling `os.getcwd()`, which returns the absolute path as a string, and then prints it to the standard output.
```

This is particularly useful for understanding complex code snippets or shell commands you may not be familiar with:

```
$ q -e 'find . -type d -name .git -exec dirname {} \; | sort'
This command searches recursively from the current directory for directories named `.git`, then uses `dirname` to output their parent directory paths, effectively listing all Git repository root directories. The results are then sorted alphabetically.
```

It can even generate explanations about technical concepts:

```
$ q -e neuroevolution
Neuroevolution is a technique that applies evolutionary algorithms to optimize artificial neural networks, typically evolving their weights, architectures, or learning rules. Instead of using gradient-based methods like backpropagation, neuroevolution treats network parameters as genomes and iteratively improves them through selection, mutation, and crossover, enabling the discovery of novel network topologies and solutions, especially useful in reinforcement learning and problems with non-differentiable objectives.
```

### Search the Web

Use the `-w` or `--web` command to search the web for up-to-date information:

```
$ q -w when was claude code released
Claude Code was released as a research preview on February 24, 2025, and became generally available on May 22, 2025. (docs.anthropic.com)
```

> **Note:** This command incurs slightly higher API usage costs compared to the commands above.

### Generate Images

Use the `-i` or `--image` command to generate 1024x1024 images:

```
$ q -i george washington riding a harley through the american civil war
Image saved to q_george_washington_riding_a_harley_through_the_american_civil_war.png.
```

> **Note:** This command incurs significantly higher API usage costs compared to the commands above. Monitor your usage closely to avoid unexpected charges.

## Multi-Turn Conversations

Use `q` without specifying a command to build on the previous response conversationally:

```
$ q -w 1998 NBA MVP
Michael Jordan won the 1997-98 NBA Most Valuable Player (MVP) award. (nba.com)
$ q how many does he have
Michael Jordan has won the NBA MVP award 5 times.
```

This is very useful for iteratively refining generated code snippets or shell commands:

```
$ q -s get cuda version
nvcc --version
$ nvcc --version
bash: nvcc: command not found
$ q command not found
cat /usr/local/cuda/version.txt
$ cat /usr/local/cuda/version.txt
cat: /usr/local/cuda/version.txt: No such file or directory
$ q file not found
nvidia-smi | grep "CUDA Version"
$ nvidia-smi | grep "CUDA Version"
| NVIDIA-SMI 560.35.02    Driver Version: 560.94    CUDA Version: 12.6 |
```

You can ask questions about the previous response:

```
$ q -c function to merge two dictionaries x and y
def merge_dictionaries(x, y):
    return {**x, **y}
$ q what is the time complexity
The time complexity of merging two dictionaries using `{**x, **y}` is O(n + m), where n is the number of elements in dictionary `x` and m is the number of elements in dictionary `y`.
```

You can even refine generated images:

```
$ q -i low poly rubber duck
Image saved to q_low_poly_rubber_duck.png.
$ q make it float in a high res bathtub
Image saved to q_make_it_float_in_a_high_res_bathtub.png.
```

## Options

Options are boolean flags that modify the behavior of `q`:

- Use the `-o` or `--overwrite` option to overwrite the previous command.
- Use the `-n` or `--no-clip` option to disable automatically saving responses to the clipboard.
- Use the `-v` or `--verbose` option to print the model parameters and message history.

You can combine multiple options using their abbreviated forms following a single hyphen:

```
$ q -w who created Linux
Linux was created by Linus Torvalds.
$ q what else did he develop
Linus Torvalds developed Git, a distributed version control system, in 2005. He also created Subsurface, a dive logging tool for scuba divers, in 2011. (en.wikipedia.org)
$ q when was it released -vo

MODEL PARAMETERS:
model: gpt-4.1-mini
max_output_tokens: 1024
temperature: 0.0
tools: [{'type': 'web_search_preview', 'search_context_size': 'low'}]

MESSAGES:
Developer: You fetch real-time data from the internet. Always respond with only the data requested. Do not provide additional information in the form of context, background, or links. The response should be less than a single sentence.
User: Fetch the following information: who created Linux.
Assistant: Linux was created by Linus Torvalds.
User: when was it released
Assistant: Linux was first released on September 17, 1991.
```
