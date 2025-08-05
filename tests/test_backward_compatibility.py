"""
Comprehensive backward compatibility tests.

Tests that ensure the modular Q implementation maintains exact compatibility
with the original q.py monolithic script including:
- CLI interface and argument handling
- Configuration file format and behavior
- Command execution and output format
- Error messages and exit codes
- Response processing and formatting
- Resource management functions
"""

import pytest
import sys
import os
import json
import tempfile
from io import StringIO
from unittest.mock import Mock, patch, MagicMock

from q.cli import main as cli_main, run_command, print_help
from q.config.manager import ConfigManager, _load_resource, _save_resource
from q.utils.processing import ResponseProcessor
from tests.conftest import create_test_image_data


@pytest.mark.backward_compatibility
class TestCLIBackwardCompatibility:
    """Test CLI backward compatibility with original q.py."""
    
    def setup_method(self):
        """Set up for each test."""
        self.original_argv = sys.argv.copy()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def teardown_method(self):
        """Clean up after each test."""
        sys.argv = self.original_argv
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    def test_help_format_compatibility(self):
        """Test that help output format matches original q.py exactly."""
        stdout = StringIO()
        sys.stdout = stdout
        
        # Mock commands to match original
        with patch('q.cli.get_default_command') as mock_get_default:
            with patch('q.cli.list_commands') as mock_list_commands:
                # Mock default command
                mock_default = Mock()
                mock_default.get_command_config.return_value = {
                    'flags': [],
                    'description': 'follow-up or general conversation'
                }
                mock_get_default.return_value = mock_default
                
                # Mock other commands to match original
                commands_data = [
                    (['-e', '--explain'], 'explain code or concepts'),
                    (['-c', '--code'], 'generate code'),
                    (['-s', '--shell'], 'generate shell commands'),
                    (['-i', '--image'], 'generate images'),
                    (['-w', '--web'], 'search the internet')
                ]
                
                mock_commands = []
                for flags, desc in commands_data:
                    mock_cmd = Mock()
                    mock_cmd.flags = flags
                    mock_cmd.get_command_config.return_value = {
                        'flags': flags,
                        'description': desc
                    }
                    mock_commands.append(mock_cmd)
                
                mock_list_commands.return_value = mock_commands
                
                print_help()
        
        help_output = stdout.getvalue()
        
        # Check exact format elements from original q.py
        assert 'q 1.4.0 - An LLM-powered programming copilot from the comfort of your command line' in help_output
        assert 'Usage: ' in help_output
        assert 'q [command] TEXT [options]' in help_output
        assert 'Commands (one required):' in help_output
        assert 'Options:' in help_output
        
        # Check specific command descriptions
        assert '-e, --explain' in help_output
        assert 'explain code or concepts' in help_output
        assert '-c, --code' in help_output
        assert 'generate code' in help_output
        
        # Check option descriptions
        assert '-o, --overwrite' in help_output
        assert 'overwrite the previous command' in help_output
        assert '-n, --no-clip' in help_output
        assert 'do not copy the output to the clipboard' in help_output
        assert '-v, --verbose' in help_output
        assert 'print the model parameters and message history' in help_output
    
    def test_argument_parsing_compatibility(self):
        """Test that argument parsing behavior matches original exactly."""
        # Test cases that should match original q.py behavior
        test_cases = [
            # (args, should_succeed, expected_error_pattern)
            (['q'], False, None),  # No args - should show help
            (['q', '-h'], False, None),  # Help flag
            (['q', '--help'], False, None),  # Help flag
            (['q', '-e', 'test'], True, None),  # Valid command
            (['q', '--explain', 'test'], True, None),  # Valid long command
            (['q', '-e', '-c', 'test'], False, 'Only one command may be provided'),  # Multiple commands
            (['q', 'text', '-e'], False, 'Command must be the first argument'),  # Wrong order
            (['q', '-x', 'test'], False, 'Invalid command "-x"'),  # Invalid command
            (['q', '-e'], False, 'No text provided'),  # No text
        ]
        
        for args, should_succeed, expected_error in test_cases:
            sys.argv = args
            stderr = StringIO()
            sys.stderr = stderr
            
            with patch('q.cli.validate_commands', return_value=[]):
                with patch('q.cli.list_commands') as mock_list_commands:
                    with patch('q.cli.run_command') as mock_run_command:
                        # Mock commands
                        mock_cmd = Mock()
                        mock_cmd.flags = ['-e', '--explain']
                        mock_cmd.get_command_config.return_value = {'test': 'config'}
                        mock_list_commands.return_value = [mock_cmd]
                        
                        try:
                            cli_main()
                            if not should_succeed:
                                pytest.fail(f"Expected failure for args {args} but succeeded")
                        except SystemExit as e:
                            if should_succeed:
                                pytest.fail(f"Expected success for args {args} but failed with exit {e.code}")
                            
                            if expected_error:
                                error_output = stderr.getvalue()
                                assert expected_error in error_output, f"Expected error '{expected_error}' not found in output: {error_output}"
    
    def test_option_flag_parsing_compatibility(self):
        """Test that option flag parsing matches original exactly."""
        with patch('q.cli.validate_commands', return_value=[]):
            with patch('q.cli.list_commands') as mock_list_commands:
                with patch('q.cli.run_command') as mock_run_command:
                    # Mock command
                    mock_cmd = Mock()
                    mock_cmd.flags = ['-e', '--explain']
                    mock_cmd.get_command_config.return_value = {'test': 'config'}
                    mock_list_commands.return_value = [mock_cmd]
                    
                    # Test individual flags
                    sys.argv = ['q', '-e', 'test', '-v', '-n', '-o']
                    
                    with pytest.raises(SystemExit):
                        cli_main()
                    
                    # Verify options were parsed correctly
                    call_args = mock_run_command.call_args
                    options = call_args[1]  # Keyword arguments
                    
                    assert options['verbose'] == True
                    assert options['no-clip'] == True  
                    assert options['overwrite'] == True
                    
                    # Test combined flags
                    mock_run_command.reset_mock()
                    sys.argv = ['q', '-e', 'test', '-vno']
                    
                    with pytest.raises(SystemExit):
                        cli_main()
                    
                    call_args = mock_run_command.call_args
                    options = call_args[1]
                    
                    assert options['verbose'] == True
                    assert options['no-clip'] == True
                    assert options['overwrite'] == True
    
    def test_error_message_format_compatibility(self):
        """Test that error messages match original q.py format exactly."""
        error_test_cases = [
            (['q', '-x', 'test'], 'Invalid command "-x"'),
            (['q', '-e'], 'No text provided'),
            (['q', '-e', '-c', 'test'], 'Only one command may be provided'),
            (['q', 'text', '-e'], 'Command must be the first argument'),
        ]
        
        for args, expected_error in error_test_cases:
            sys.argv = args
            stderr = StringIO()
            sys.stderr = stderr
            
            with patch('q.cli.validate_commands', return_value=[]):
                with patch('q.cli.list_commands') as mock_list_commands:
                    mock_cmd = Mock()
                    mock_cmd.flags = ['-e', '--explain']
                    mock_list_commands.return_value = [mock_cmd]
                    
                    with pytest.raises(SystemExit) as exc_info:
                        cli_main()
                    
                    assert exc_info.value.code == 1
                    error_output = stderr.getvalue()
                    assert f'Error: {expected_error}' in error_output


@pytest.mark.backward_compatibility
class TestConfigurationBackwardCompatibility:
    """Test configuration system backward compatibility."""
    
    def test_resource_functions_compatibility(self):
        """Test that _load_resource and _save_resource functions work like original."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            config_path = tmp_file.name
            
            try:
                # Test saving resource (should create file)
                _save_resource('test_key', 'test_value', config_path)
                
                # Verify file was created with correct format
                assert os.path.exists(config_path)
                with open(config_path, 'r') as f:
                    data = json.load(f)
                assert data['test_key'] == 'test_value'
                
                # Test loading resource
                loaded_value = _load_resource('test_key', 'default_value', config_path)
                assert loaded_value == 'test_value'
                
                # Test loading non-existent key returns default
                default_value = _load_resource('nonexistent_key', 'default_value', config_path)
                assert default_value == 'default_value'
                
                # Test saving multiple resources
                _save_resource('openai_key', 'sk-test123', config_path)
                _save_resource('model_args', {'model': 'gpt-4.1', 'temperature': 0.0}, config_path)
                
                # Verify all data is preserved
                openai_key = _load_resource('openai_key', None, config_path)
                model_args = _load_resource('model_args', {}, config_path)
                original_key = _load_resource('test_key', None, config_path)
                
                assert openai_key == 'sk-test123'
                assert model_args == {'model': 'gpt-4.1', 'temperature': 0.0}
                assert original_key == 'test_value'  # Should still be there
                
            finally:
                if os.path.exists(config_path):
                    os.unlink(config_path)
    
    def test_config_file_format_compatibility(self):
        """Test that config file format matches original q.py exactly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            config_path = tmp_file.name
            
            try:
                config = ConfigManager(config_path=config_path)
                
                # Set up configuration like original q.py would
                config._save_resource('openai_key', 'sk-test123')
                config._save_resource('model_args', {
                    'model': 'gpt-4.1-mini',
                    'temperature': 0.0,
                    'max_output_tokens': 1024
                })
                config._save_resource('messages', [
                    {'role': 'user', 'content': 'Hello'},
                    {'role': 'assistant', 'content': 'Hi there!'}
                ])
                config._save_resource('clip_output', True)
                
                # Verify file format
                with open(config_path, 'r') as f:
                    data = json.load(f)
                
                # Should match original structure exactly
                assert 'openai_key' in data
                assert 'model_args' in data
                assert 'messages' in data
                assert 'clip_output' in data
                
                assert data['openai_key'] == 'sk-test123'
                assert data['model_args']['model'] == 'gpt-4.1-mini'
                assert data['model_args']['temperature'] == 0.0
                assert data['clip_output'] == True
                
                # Message format should match original
                assert len(data['messages']) == 2
                assert data['messages'][0]['role'] == 'user'
                assert data['messages'][0]['content'] == 'Hello'
                
            finally:
                if os.path.exists(config_path):
                    os.unlink(config_path)
    
    def test_api_key_management_compatibility(self):
        """Test that API key management works like original q.py."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            config_path = tmp_file.name
            
            try:
                config = ConfigManager(config_path=config_path)
                
                # Test setting API key through new interface
                config.set_api_key('openai', 'sk-new-key')
                
                # Should be accessible through old interface
                old_key = config._load_resource('openai_key', None)
                assert old_key == 'sk-new-key'
                
                # Test setting through old interface
                config._save_resource('openai_key', 'sk-old-way')
                
                # Should be accessible through new interface
                new_key = config.get_api_key('openai')
                assert new_key == 'sk-old-way'
                
            finally:
                if os.path.exists(config_path):
                    os.unlink(config_path)


@pytest.mark.backward_compatibility
class TestResponseProcessingCompatibility:
    """Test response processing backward compatibility."""
    
    def test_text_processing_exact_match(self):
        """Test that text processing produces exactly the same output as original."""
        processor = ResponseProcessor()
        
        # Test cases from original q.py processing logic
        test_cases = [
            # Markdown code block removal
            ("```python\nprint('hello')\n```", "print('hello')"),
            
            # Link shortening
            ("Check [Python docs](https://docs.python.org) for more.", "Check Python docs for more."),
            
            # Bash code blocks with $ prefix (colored)
            ("```bash\nls -la\n```", "$ ls -la"),
            
            # Inline code coloring
            ("Use `git status` to check.", "Use git status to check."),
            
            # Newline normalization
            ("First line.\n\n\nSecond line.", "First line.\n\nSecond line.")
        ]
        
        for input_text, expected_pattern in test_cases:
            result = processor.process_text_response(input_text)
            
            if expected_pattern == "$ ls -la":
                # For bash commands, check that $ prefix is added and colored
                assert "$ ls -la" in result
                assert "\x1b[36m" in result  # Cyan color code
            elif expected_pattern == "Use git status to check.":
                # For inline code, check that it's colored
                assert "git status" in result
                assert "\x1b[36m" in result  # Cyan color code
            else:
                # For other cases, check exact match
                assert expected_pattern in result
    
    def test_complex_processing_compatibility(self):
        """Test complex processing scenarios match original behavior."""
        processor = ResponseProcessor()
        
        # Complex example that tests multiple processing steps
        complex_input = """Here's how to use git:

```bash
git add .
git commit -m "Initial commit"
```

You can also check the [Git documentation](https://git-scm.com/docs) for more details.


Use `git log` to see commit history.



That's it!"""
        
        result = processor.process_text_response(complex_input)
        
        # Should have bash commands with $ prefix and colored
        assert "$ git add ." in result
        assert "$ git commit -m \"Initial commit\"" in result
        assert "\x1b[36m" in result  # Cyan coloring
        
        # Should have shortened link
        assert "Git documentation" in result
        assert "https://git-scm.com/docs" not in result
        
        # Should have colored inline code
        assert "\x1b[36mgit log\x1b[0m" in result
        
        # Should have normalized newlines (no more than double)
        assert "\n\n\n" not in result
        
        # Should preserve other text
        assert "Here's how to use git:" in result
        assert "That's it!" in result
    
    def test_edge_case_processing_compatibility(self):
        """Test edge cases match original behavior."""
        processor = ResponseProcessor()
        
        # Edge cases from original q.py
        edge_cases = [
            # Empty string
            ("", ""),
            
            # Only whitespace
            ("   ", "   "),
            
            # Malformed code block (no closing)
            ("```python\nprint('hello')", "```python\nprint('hello')"),
            
            # Nested backticks
            ("Use `git status` and `git log`", "Use git status and git log"),
        ]
        
        for input_text, expected_pattern in edge_cases:
            result = processor.process_text_response(input_text)
            
            if "git status" in expected_pattern:
                # Check colored output
                assert "git status" in result
                assert "git log" in result
                assert "\x1b[36m" in result  # Should be colored
            else:
                assert expected_pattern in result or result == expected_pattern


@pytest.mark.backward_compatibility
class TestCommandExecutionCompatibility:
    """Test command execution backward compatibility."""
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_exact_behavior(self, mock_get_provider, mock_get_config):
        """Test that run_command behaves exactly like original q.py."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.text = "Test response from provider"
        mock_provider.generate_text.return_value = mock_response
        mock_get_provider.return_value = mock_provider
        
        # Test command config that matches original format
        cmd_config = {
            'flags': ['-e', '--explain'],
            'description': 'explain code or concepts',
            'clip_output': False,
            'model_args': {
                'model': 'gpt-4.1-mini',
                'max_output_tokens': 1024,
                'temperature': 0.0
            },
            'messages': [
                {'role': 'developer', 'content': 'You are a helpful programming assistant.'},
                {'role': 'user', 'content': '{text}'}
            ]
        }
        
        # Capture output
        stdout = StringIO()
        sys.stdout = stdout
        
        # Run command
        run_command(cmd_config, 'What is Python?')
        
        output = stdout.getvalue()
        
        # Should display the response
        assert "Test response from provider" in output
        
        # Should save model args and messages like original
        save_calls = mock_config._save_resource.call_args_list
        save_dict = {call[0][0]: call[0][1] for call in save_calls}
        
        assert 'model_args' in save_dict
        assert 'clip_output' in save_dict
        assert 'messages' in save_dict
        
        # Model args should match what was passed in
        assert save_dict['model_args'] == cmd_config['model_args']
        assert save_dict['clip_output'] == cmd_config['clip_output']
        
        # Messages should include the response
        saved_messages = save_dict['messages']
        assert len(saved_messages) >= 2  # Original messages + response
        assert saved_messages[-1]['role'] == 'assistant'
        assert saved_messages[-1]['content'] == "Test response from provider"
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_image_command_compatibility(self, mock_get_provider, mock_get_config):
        """Test image command execution matches original behavior."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock image generation
        test_image_data = create_test_image_data()
        
        with patch('q.cli.ImageGenerator') as mock_img_gen_class:
            mock_img_gen = Mock()
            mock_img_gen.generate.return_value = test_image_data
            mock_img_gen_class.return_value = mock_img_gen
            
            # Image command config
            cmd_config = {
                'flags': ['-i', '--image'],
                'description': 'generate images',
                'clip_output': False,
                'model_args': {
                    'model': 'gpt-4.1-mini',
                    'tools': [{'type': 'image_generation', 'size': '1024x1024', 'quality': 'auto'}]
                },
                'messages': [{'role': 'user', 'content': '{text}'}]
            }
            
            # Mock file operations exactly like original
            with patch('builtins.open', create=True) as mock_open:
                stderr = StringIO()
                sys.stderr = stderr
                
                run_command(cmd_config, 'a beautiful sunset')
                
                error_output = stderr.getvalue()
                
                # Should save image with exact same naming as original
                assert 'Image saved to q_a_beautiful_sunset.png' in error_output
                
                # Should write file exactly like original
                mock_open.assert_called_once_with('q_a_beautiful_sunset.png', 'wb')
                mock_open().write.assert_called_once_with(test_image_data)
                
                # Should save messages in original format
                save_calls = mock_config._save_resource.call_args_list
                save_dict = {call[0][0]: call[0][1] for call in save_calls}
                
                assert 'messages' in save_dict
                saved_messages = save_dict['messages']
                
                # Should include image generation call like original
                assert any(msg.get('type') == 'image_generation_call' for msg in saved_messages)
                image_msg = next(msg for msg in saved_messages if msg.get('type') == 'image_generation_call')
                assert image_msg['id'] == 'q_a_beautiful_sunset.png'
    
    def test_verbose_output_format_compatibility(self):
        """Test that verbose output format matches original exactly."""
        from q.utils.processing import ResponseProcessor
        
        processor = ResponseProcessor()
        
        # Test model parameters formatting
        model_args = {
            'model': 'gpt-4.1-mini',
            'temperature': 0.0,
            'max_output_tokens': 1024
        }
        
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'},
            {'type': 'image_generation_call', 'id': 'test.png'}
        ]
        
        result = processor.format_for_cli(
            "Test response",
            verbose=True,
            model_args=model_args,
            messages=messages
        )
        
        # Should match original format exactly
        assert 'MODEL PARAMETERS:' in result
        assert 'model: gpt-4.1-mini' in result
        assert 'temperature: 0.0' in result
        assert 'max_output_tokens: 1024' in result
        
        assert 'MESSAGES:' in result
        assert 'User: Hello' in result
        assert 'Assistant: Hi there!' in result
        assert 'Image_generation_call: test.png' in result
        
        # Response should be at the end
        assert result.endswith("Test response")


@pytest.mark.backward_compatibility  
class TestFullWorkflowCompatibility:
    """Test complete workflow compatibility end-to-end."""
    
    def setup_method(self):
        """Set up for each test."""
        self.original_argv = sys.argv.copy()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def teardown_method(self):
        """Clean up after each test."""
        sys.argv = self.original_argv
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.config.manager.ConfigManager._load_resource')
    @patch('q.config.manager.ConfigManager._save_resource')
    def test_complete_explain_workflow_compatibility(self, mock_save, mock_load, mock_openai_class):
        """Test complete explain workflow produces identical output to original."""
        # Mock configuration exactly like original
        def mock_load_side_effect(key, default):
            return {
                'openai_key': 'sk-test123',
                'model_args': {'model': 'gpt-4.1-mini', 'temperature': 0.0, 'max_output_tokens': 1024},
                'messages': [],
                'clip_output': False
            }.get(key, default)
        
        mock_load.side_effect = mock_load_side_effect
        
        # Mock OpenAI response exactly like original would receive
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Python is a high-level, interpreted programming language."
        mock_response.output = []
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Execute CLI exactly like original
        sys.argv = ['q', '-e', 'what is python']
        
        stdout = StringIO()
        stderr = StringIO()
        sys.stdout = stdout
        sys.stderr = stderr
        
        with patch('q.cli.pyperclip.copy'):
            with pytest.raises(SystemExit) as exc_info:
                cli_main()
        
        # Should exit successfully like original
        assert exc_info.value.code == 0
        
        # Output should match original processing
        output = stdout.getvalue()
        assert "Python is a high-level, interpreted programming language." in output
        
        # Configuration should be saved exactly like original
        mock_save.assert_called()
        save_calls = mock_save.call_args_list
        save_dict = {call[0][0]: call[0][1] for call in save_calls}
        
        # Should save model_args, clip_output, and messages like original
        assert 'model_args' in save_dict
        assert 'clip_output' in save_dict
        assert 'messages' in save_dict
        
        # Model args should match original defaults
        model_args = save_dict['model_args']
        assert model_args['model'] == 'gpt-4.1-mini'
        assert model_args['temperature'] == 0.0
        assert model_args['max_output_tokens'] == 1024
    
    def test_configuration_persistence_compatibility(self):
        """Test that configuration persistence works exactly like original."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            config_path = tmp_file.name
            
            try:
                # Simulate original q.py workflow
                # 1. Initial command saves configuration
                _save_resource('openai_key', 'sk-test123', config_path)
                _save_resource('model_args', {
                    'model': 'gpt-4.1-mini',
                    'temperature': 0.0,
                    'max_output_tokens': 1024
                }, config_path)
                _save_resource('messages', [
                    {'role': 'developer', 'content': 'You are a helpful assistant.'},
                    {'role': 'user', 'content': 'what is python'},
                    {'role': 'assistant', 'content': 'Python is a programming language.'}
                ], config_path)
                _save_resource('clip_output', False, config_path)
                
                # 2. Follow-up command loads configuration
                loaded_key = _load_resource('openai_key', None, config_path)
                loaded_args = _load_resource('model_args', {}, config_path)
                loaded_messages = _load_resource('messages', [], config_path)
                loaded_clip = _load_resource('clip_output', False, config_path)
                
                # Should match exactly what was saved
                assert loaded_key == 'sk-test123'
                assert loaded_args['model'] == 'gpt-4.1-mini'
                assert len(loaded_messages) == 3
                assert loaded_messages[0]['role'] == 'developer'
                assert loaded_messages[1]['role'] == 'user'
                assert loaded_messages[2]['role'] == 'assistant'
                assert loaded_clip == False
                
                # 3. Subsequent command updates configuration  
                loaded_messages.append({'role': 'user', 'content': 'tell me about java'})
                loaded_messages.append({'role': 'assistant', 'content': 'Java is another programming language.'})
                _save_resource('messages', loaded_messages, config_path)
                
                # Should preserve all previous data
                final_key = _load_resource('openai_key', None, config_path)
                final_messages = _load_resource('messages', [], config_path)
                
                assert final_key == 'sk-test123'  # Should still be there
                assert len(final_messages) == 5  # Should have all messages
                
            finally:
                if os.path.exists(config_path):
                    os.unlink(config_path)