"""
Comprehensive unit tests for response processing utilities.

Tests the text processing and formatting functionality including:
- Markdown code block removal
- Link shortening from web search
- Bash code block formatting
- Inline code formatting
- Newline normalization
- CLI output formatting
"""

import pytest
from termcolor import colored

from q.utils.processing import ResponseProcessor


@pytest.mark.unit
class TestResponseProcessor:
    """Test ResponseProcessor functionality."""
    
    def test_process_text_response_basic(self):
        """Test basic text response processing."""
        processor = ResponseProcessor()
        
        text = "This is a simple response."
        result = processor.process_text_response(text)
        
        assert result == "This is a simple response."
    
    def test_remove_markdown_code_blocks(self):
        """Test removal of markdown formatting from code responses."""
        processor = ResponseProcessor()
        
        # Single-line code block
        text = "```python\nprint('hello')\n```"
        result = processor.process_text_response(text)
        assert result == "print('hello')"
        
        # Multi-line code block
        text = "```python\ndef hello():\n    print('world')\n```"
        result = processor.process_text_response(text)
        assert result == "def hello():\n    print('world')"
        
        # Code block with language specification
        text = "```javascript\nconsole.log('hello');\n```"
        result = processor.process_text_response(text)
        assert result == "console.log('hello');"
        
        # Code block without language
        text = "```\necho 'hello'\n```" 
        result = processor.process_text_response(text)
        assert result == "echo 'hello'"
    
    def test_preserve_non_code_block_content(self):
        """Test that non-code-block content is preserved."""
        processor = ResponseProcessor()
        
        text = "Here's some code: ```python\nprint('hello')\n``` and some more text."
        result = processor.process_text_response(text)
        
        # Should only remove the outermost complete code block if it wraps the entire response
        # In this case, it doesn't wrap the entire response, so it should be processed differently
        assert "print('hello')" in result
    
    def test_shorten_links_from_web_search(self):
        """Test shortening of links from web search responses."""
        processor = ResponseProcessor()
        
        # Standard markdown link
        text = "Check out [Python documentation](https://docs.python.org/3/) for more info."
        result = processor.process_text_response(text)
        assert result == "Check out Python documentation for more info."
        
        # Multiple links
        text = "Visit [Google](https://google.com) or [GitHub](https://github.com) for resources."
        result = processor.process_text_response(text)
        assert result == "Visit Google or GitHub for resources."
        
        # Link with complex URL
        text = "See [this article](https://example.com/path/to/article?param=value&other=123) for details."
        result = processor.process_text_response(text)
        assert result == "See this article for details."
    
    def test_convert_bash_code_blocks(self):
        """Test conversion of bash code blocks to colored text with $ prefix."""
        processor = ResponseProcessor()
        
        # Single bash command
        text = "```bash\nls -la\n```"
        result = processor.process_text_response(text)
        expected = colored('$ ls -la', 'cyan')
        assert result == expected
        
        # Multiple bash commands
        text = "```bash\ncd /home\nls -la\n```"
        result = processor.process_text_response(text) 
        expected = colored('$ cd /home\n$ ls -la', 'cyan')
        assert result == expected
        
        # Bash block with extra newlines
        text = "```bash\n\nls -la\n\n```"
        result = processor.process_text_response(text)
        expected = colored('$ ls -la', 'cyan')
        assert result == expected
    
    def test_convert_non_bash_code_blocks(self):
        """Test conversion of non-bash code blocks to colored text."""
        processor = ResponseProcessor()
        
        # Python code block
        text = "```python\nprint('hello')\n```"
        result = processor.process_text_response(text)
        expected = colored("print('hello')", 'cyan')
        assert result == expected
        
        # JavaScript code block
        text = "```javascript\nconsole.log('hello');\n```"
        result = processor.process_text_response(text)
        expected = colored("console.log('hello');", 'cyan')
        assert result == expected
        
        # Code block without language specifier
        text = "```\necho hello\n```"
        result = processor.process_text_response(text)
        expected = colored("echo hello", 'cyan')
        assert result == expected
        
        # Multi-line code block
        text = "```python\ndef hello():\n    print('world')\n```"
        result = processor.process_text_response(text)
        expected = colored("def hello():\n    print('world')", 'cyan')
        assert result == expected
    
    def test_convert_inline_code(self):
        """Test conversion of inline code to colored text."""
        processor = ResponseProcessor()
        
        # Single inline code
        text = "Use the `print()` function to output text."
        result = processor.process_text_response(text)
        expected = f"Use the {colored('print()', 'cyan')} function to output text."
        assert result == expected
        
        # Multiple inline code snippets
        text = "Compare `list.append()` with `list.extend()` methods."
        result = processor.process_text_response(text)
        expected = f"Compare {colored('list.append()', 'cyan')} with {colored('list.extend()', 'cyan')} methods."
        assert result == expected
        
        # Inline code with special characters
        text = "The regex pattern `[a-zA-Z0-9]+` matches alphanumeric characters."
        result = processor.process_text_response(text)
        expected = f"The regex pattern {colored('[a-zA-Z0-9]+', 'cyan')} matches alphanumeric characters."
        assert result == expected
    
    def test_normalize_newlines(self):
        """Test conversion of multiple newlines to double newlines."""
        processor = ResponseProcessor()
        
        # Triple newlines
        text = "First paragraph.\n\n\nSecond paragraph."
        result = processor.process_text_response(text)
        assert result == "First paragraph.\n\nSecond paragraph."
        
        # Many newlines
        text = "First paragraph.\n\n\n\n\nSecond paragraph."
        result = processor.process_text_response(text)
        assert result == "First paragraph.\n\nSecond paragraph."
        
        # Mixed newlines with spaces
        text = "First paragraph.\n \n\n  \n\nSecond paragraph."
        result = processor.process_text_response(text)
        # Note: spaces between newlines are preserved
        assert result == "First paragraph.\n \n  \n\nSecond paragraph."
    
    def test_complex_processing_chain(self):
        """Test complex processing with multiple transformations."""
        processor = ResponseProcessor()
        
        text = """Here's how to use git:
        
```bash
git add .
git commit -m "message"
```

You can also check [Git documentation](https://git-scm.com/docs) for more info.

Use `git status` to check your repository status.


The end."""
        
        result = processor.process_text_response(text)
        
        # Should have bash commands with $ prefix and colored
        assert "$ git add ." in result
        assert "$ git commit -m \"message\"" in result
        
        # Should have shortened link
        assert "Git documentation" in result
        assert "https://git-scm.com/docs" not in result
        
        # Should have colored inline code
        assert colored('git status', 'cyan') in result
        
        # Should have normalized newlines (no triple+ newlines)
        assert "\n\n\n" not in result
    
    def test_edge_cases(self):
        """Test edge cases and special scenarios."""
        processor = ResponseProcessor()
        
        # Empty string
        assert processor.process_text_response("") == ""
        
        # Only whitespace
        assert processor.process_text_response("   \n\n   ") == "   \n\n   "
        
        # Only code block
        text = "```python\nprint('hello')\n```"
        result = processor.process_text_response(text)
        assert result == colored("print('hello')", 'cyan')
        
        # Malformed code block (no closing)
        text = "```python\nprint('hello')"
        result = processor.process_text_response(text)
        assert result == "```python\nprint('hello')"  # Should remain unchanged
        
        # Malformed inline code (no closing backtick)
        text = "Use the `print() function"
        result = processor.process_text_response(text)
        assert result == "Use the `print() function"  # Should remain unchanged
        
        # Nested backticks (should not be processed as code)
        text = "The string `contains a ` backtick` is tricky."
        result = processor.process_text_response(text)
        # Should process the first complete inline code segment
        expected = f"The string {colored('contains a ', 'cyan')} backtick` is tricky."
        assert result == expected
    
    def test_format_for_cli_basic(self):
        """Test basic CLI formatting without verbose mode."""
        processor = ResponseProcessor()
        
        response = "This is a response."
        result = processor.format_for_cli(response, verbose=False)
        
        assert result == "This is a response."
    
    def test_format_for_cli_verbose_with_model_args(self):
        """Test CLI formatting with verbose mode and model arguments."""
        processor = ResponseProcessor()
        
        response = "This is a response."
        model_args = {
            'model': 'gpt-4.1',
            'temperature': 0.5,
            'max_tokens': 1024
        }
        
        result = processor.format_for_cli(response, verbose=True, model_args=model_args)
        
        assert colored('MODEL PARAMETERS:', 'red') in result
        assert colored('model:', 'green') in result
        assert 'gpt-4.1' in result
        assert colored('temperature:', 'green') in result
        assert '0.5' in result
        assert colored('max_tokens:', 'green') in result
        assert '1024' in result
        assert "This is a response." in result
    
    def test_format_for_cli_verbose_with_messages(self):
        """Test CLI formatting with verbose mode and message history."""
        processor = ResponseProcessor()
        
        response = "This is a response."
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'},
            {'type': 'image_generation_call', 'id': 'image.png'}
        ]
        
        result = processor.format_for_cli(response, verbose=True, messages=messages)
        
        assert colored('\nMESSAGES:', 'red') in result
        assert colored('User:', 'green') in result
        assert 'Hello' in result
        assert colored('Assistant:', 'green') in result
        assert 'Hi there!' in result
        assert colored('Image_generation_call:', 'green') in result
        assert 'image.png' in result
        assert "This is a response." in result
    
    def test_format_for_cli_verbose_complete(self):
        """Test CLI formatting with verbose mode, model args, and messages."""
        processor = ResponseProcessor()
        
        response = "This is a response."
        model_args = {'model': 'gpt-4.1', 'temperature': 0.0}
        messages = [{'role': 'user', 'content': 'Test message'}]
        
        result = processor.format_for_cli(
            response, 
            verbose=True, 
            model_args=model_args, 
            messages=messages
        )
        
        # Should contain both model parameters and messages sections
        assert colored('MODEL PARAMETERS:', 'red') in result
        assert colored('\nMESSAGES:', 'red') in result
        assert "This is a response." in result
        
        # Should be properly formatted with sections before response
        lines = result.split('\n')
        response_line_index = None
        for i, line in enumerate(lines):
            if "This is a response." in line:
                response_line_index = i
                break
        
        assert response_line_index is not None
        assert response_line_index > 0  # Response should not be first line
    
    def test_bash_command_formatting_edge_cases(self):
        """Test edge cases in bash command formatting."""
        processor = ResponseProcessor()
        
        # Bash command with pipe
        text = "```bash\nls -la | grep python\n```"
        result = processor.process_text_response(text)
        expected = colored('$ ls -la | grep python', 'cyan')
        assert result == expected
        
        # Bash command with quotes
        text = "```bash\necho 'hello world'\n```"
        result = processor.process_text_response(text)
        expected = colored("$ echo 'hello world'", 'cyan')
        assert result == expected
        
        # Multi-line bash with comments
        text = "```bash\n# This is a comment\nls -la\n# Another comment\ncd /home\n```"
        result = processor.process_text_response(text)
        expected = colored('$ # This is a comment\n$ ls -la\n$ # Another comment\n$ cd /home', 'cyan')
        assert result == expected
    
    def test_processing_order(self):
        """Test that processing steps happen in correct order."""
        processor = ResponseProcessor()
        
        # This text should test the processing order
        text = "```python\nprint('Check [link](http://example.com) and `code`')\n```"
        result = processor.process_text_response(text)
        
        # First: remove outer code block markdown (if it wraps entire response)
        # Then: shorten links
        # Then: convert remaining code blocks 
        # Then: convert inline code
        # Then: normalize newlines
        
        # Since this is a complete code block, it should be treated as code output
        expected = colored("print('Check link and code')", 'cyan')
        assert result == expected
    
    def test_mixed_content_processing(self):
        """Test processing of mixed content types."""
        processor = ResponseProcessor()
        
        text = """To install Python packages:

```bash
pip install requests
```

You can also check the [pip documentation](https://pip.pypa.io/en/stable/) for more details.

Use `pip list` to see installed packages.

```python
import requests
response = requests.get('https://api.example.com')
```

That's it!"""
        
        result = processor.process_text_response(text)
        
        # Bash block should have $ prefix
        assert colored('$ pip install requests', 'cyan') in result
        
        # Link should be shortened
        assert "pip documentation" in result
        assert "https://pip.pypa.io/en/stable/" not in result
        
        # Inline code should be colored
        assert colored('pip list', 'cyan') in result
        
        # Python code block should be colored
        assert colored("import requests\nresponse = requests.get('https://api.example.com')", 'cyan') in result
    
    def test_static_method_usage(self):
        """Test that static methods can be used without instantiation."""
        # Should be able to call static methods directly
        text = "```bash\necho hello\n```"
        result = ResponseProcessor.process_text_response(text)
        expected = colored('$ echo hello', 'cyan')
        assert result == expected
        
        # Should also work with instantiation
        processor = ResponseProcessor()
        result2 = processor.process_text_response(text)
        assert result == result2


@pytest.mark.integration
class TestResponseProcessorIntegration:
    """Integration tests for response processor."""
    
    def test_integration_with_real_responses(self):
        """Test processor with realistic LLM responses."""
        processor = ResponseProcessor()
        
        # Simulate a code explanation response
        response = """Python decorators are a design pattern that allows you to modify or extend the behavior of functions or classes without permanently modifying their code.

Here's a simple example:

```python
def my_decorator(func):
    def wrapper():
        print("Something before the function")
        func()
        print("Something after the function")
    return wrapper

@my_decorator
def say_hello():
    print("Hello!")

say_hello()
```

You can learn more about decorators in the [Python documentation](https://docs.python.org/3/glossary.html#term-decorator).

Use `help(functools)` to explore built-in decorator utilities."""
        
        result = processor.process_text_response(response)
        
        # Should preserve the explanation text
        assert "Python decorators are a design pattern" in result
        
        # Should color the code block
        assert colored("def my_decorator(func):", 'cyan') in result
        
        # Should shorten the link
        assert "Python documentation" in result
        assert "https://docs.python.org/3/glossary.html#term-decorator" not in result
        
        # Should color inline code
        assert colored('help(functools)', 'cyan') in result
    
    def test_integration_with_shell_command_response(self):
        """Test processor with shell command responses."""
        processor = ResponseProcessor()
        
        response = """To find large files in your current directory, you can use:

```bash
find . -type f -size +100M -ls
```

For more advanced searching, check the [find manual](https://man7.org/linux/man-pages/man1/find.1.html).

You can also use `du -h --max-depth=1` to see directory sizes."""
        
        result = processor.process_text_response(response)
        
        # Bash command should have $ prefix and be colored
        assert colored('$ find . -type f -size +100M -ls', 'cyan') in result
        
        # Link should be shortened
        assert "find manual" in result
        assert "https://man7.org/linux/man-pages/man1/find.1.html" not in result
        
        # Inline code should be colored
        assert colored('du -h --max-depth=1', 'cyan') in result
    
    def test_performance_with_large_text(self):
        """Test processor performance with large text."""
        import time
        
        processor = ResponseProcessor()
        
        # Create large text with various elements
        large_text = """This is a large response. """ * 1000
        large_text += "\n\n```python\n"
        large_text += "print('hello')\n" * 1000
        large_text += "```\n\n"
        large_text += "Check [this link](https://example.com) " * 100
        large_text += "\n\nUse `code` " * 100
        
        start_time = time.time()
        result = processor.process_text_response(large_text)
        end_time = time.time()
        
        # Should complete in reasonable time (under 1 second)
        assert (end_time - start_time) < 1.0
        
        # Should still process correctly
        assert colored("print('hello')", 'cyan') in result
        assert "this link" in result
        assert colored('code', 'cyan') in result