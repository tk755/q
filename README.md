# Overview
`q` is an LLM-powered programming copilot from the comfort of your command line. It can generate code snippets, shell commands, technical explanations, web searches, and even images. Through multi-turn conversations, it can build, debug, and refine complex solutions iteratively. It even saves generated code and commands to your clipboard, so you can paste it wherever you need it.

Currently `q` uses the OpenAI API, but support for other LLM providers is planned in the future.

# Installation

Requires Python 3.8+ and the following dependencies:

```
pip install colorama openai pyperclip termcolor
```

Download the script to a directory in your path (e.g. `~/.local/bin/`) and make it executable:

```
wget -qO ~/.local/bin/q https://raw.githubusercontent.com/tk755/q/refs/heads/main/q && chmod +x ~/.local/bin/q
```

The first time `q` is prompted, you will be asked for an OpenAI API key which you can create [here](https://platform.openai.com/api-keys).

# Usage

The basic syntax is `q [command] TEXT [options]`. `q` accepts at most one command and any number of options. Any arguments between the command and options is treated as the input text.

`q` saves generated code snippets and shell commands to your clipboard so you can paste it wherever you need it. This only works on non-headless environments (no VMs and Docker containers); check [here](https://pyperclip.readthedocs.io/en/latest/index.html#not-implemented-error) if it doesn't work.

For a full list of commands and options, run `q -h`.

## Commands

Each command runs a tailored LLM prompt using the OpenAI API and returns the parsed response.

### Generate Code

Use the `-c` or `--code` command to generate code snippets:

```
$ q -c copy user input to clipboard
import pyperclip

user_input = input("Enter text to copy to clipboard: ")
pyperclip.copy(user_input)
```

By default this generates Python code, but you can specify a different programming language in the prompt itself (or [modify the default value](#modifying-default-values)):

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

By default this generates Bash commands for a Linux system, but you can specify a different shell or OS in the prompt itself (or [modify the default value](#modifying-default-values)):

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

Use the `-e` or `--explain` command to generate a concise explanation for code or shell commands:

```
$ q -e 'print(os.getcwd())'
`print(os.getcwd())` outputs the current working directory of the Python process by calling `os.getcwd()`, which returns the absolute path as a string, and then prints it to the standard output.
```

This is particularly useful for understanding complex code or shell commands you may not be familiar with:

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

Use the `-w` or `--web` command to search the web for up-to-date information (note: this is slightly expensive):

```
$ q -w highest qbit computer
As of July 2025, the quantum computer with the highest number of qubits is Atom Computing's processor, which has 1,180 qubits. (spinquanta.com)
```

### Generate Images

Use the `-i` or `--image` command to generate 1024x1024 images (note: this is very expensive):

```
$ q -i george washington riding a harley through the american civil war
Image saved to q_george_washington_riding_a_harley_through_the_american_civil_war.png.
```

## Multi-Turn Conversations

Use `q` without specifying a command to build on the previous response conversationally:

```
$ q -w nba champions
The Oklahoma City Thunder won the 2025 NBA Finals, defeating the Indiana Pacers 4-3. (nba.com)
$ q final game score
The Oklahoma City Thunder defeated the Indiana Pacers 103-91 in Game 7 of the 2025 NBA Finals on June 22, 2025. (espn.com)
```

This is very useful for iteratively refining generated code or shell commands:

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

And ask follow-up questions about the previous response:

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
- Use the `-n` or `--no-clip` option to disable automatically storing responses to the clipboard.
- Use the `-v` or `--verbose` option to print the model parameters and message history.

You can combine multiple options using their abbreviated forms following a single hyphen:

```
$ q -p knock knock
Who's there?
$ q apple
Apple who?
$ q orange -vo

MODEL PARAMETERS:
model: gpt-4o
max_tokens: 256
temperature: 0.25
frequency_penalty: 0
presence_penalty: 0
top_p: 1

MESSAGES:
System: You are a helpful and knowledgeable AI assistant.
User: knock knock
Assistant: Who's there?
User: orange
Assistant: Orange who?
```

# Customization

`q` was designed to be easily customizable to suit any programmer's needs.

## Modifying Default Values

The following constants can be modified in the script to change the default behavior of `q`:
- `MINI_LLM`: the default model for fast and cheap responses.
- `FULL_LLM`: the default model for long and detailed responses.
- `DEFAULT_MODEL_ARGS`: the default model arguments used by all commands if not overrided.
- `DEFAULT_CODE`: the default language for code generation used by the `-c` command.
- `DEFAULT_SHELL`: the default system for shell command generation used by the `-s` command.

## Adding New Commands

Add a new command to `q` by inserting a new dictionary in the `COMMANDS` list with the following keys:
- `flags` *(required)*: a list of flags to invoke the command.
- `description` *(required)*: a brief description of the command shown in the help message.
- `messages` *(required)*: the instructions sent to the LLM, using `{text}` as a placeholder for the input text.
- `model_args` *(optional)*: override default model arguments set in `DEFAULT_MODEL_ARGS` or set new arguments.
- `clip_output` *(optional)*: set to `True` to copy the output to the clipboard; `False` by default.

Refer to the existing commands in the script for examples.
