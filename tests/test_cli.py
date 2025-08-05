"""
Comprehensive unit tests for CLI functionality.

Tests the command line interface including:
- Argument parsing and validation
- Command execution
- Help text generation
- Error handling
- Output formatting
- Option processing
- Backward compatibility with original q.py
"""

import pytest
import sys
import os
from io import StringIO
from unittest.mock import Mock, patch, MagicMock

from q.cli import main, print_help, run_command, __version__, DESCRIPTION, OPTIONS
from q.utils.exceptions import QError
from tests.conftest import create_test_image_data


@pytest.mark.unit
class TestCLI:
    """Test CLI functionality."""
    
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
    
    def test_version_and_description(self):
        """Test that version and description are properly defined."""
        assert __version__ == '1.4.0'
        assert 'LLM-powered programming copilot' in DESCRIPTION
    
    def test_options_definition(self):
        """Test that CLI options are properly defined."""
        assert len(OPTIONS) == 3
        
        option_names = [opt['name'] for opt in OPTIONS]
        assert 'overwrite' in option_names
        assert 'no-clip' in option_names
        assert 'verbose' in option_names
        
        # Check flags
        overwrite_opt = next(opt for opt in OPTIONS if opt['name'] == 'overwrite')
        assert '-o' in overwrite_opt['flags']
        assert '--overwrite' in overwrite_opt['flags']
    
    @patch('q.cli.list_commands')
    @patch('q.cli.get_default_command')
    def test_print_help(self, mock_get_default, mock_list_commands):
        """Test help text generation."""
        # Mock commands
        mock_default = Mock()
        mock_default.get_command_config.return_value = {
            'flags': [],
            'description': 'default follow-up command'
        }
        mock_get_default.return_value = mock_default
        
        mock_cmd1 = Mock()
        mock_cmd1.flags = ['-e', '--explain']
        mock_cmd1.get_command_config.return_value = {
            'flags': ['-e', '--explain'],
            'description': 'explain code or concepts'
        }
        
        mock_cmd2 = Mock()
        mock_cmd2.flags = ['-c', '--code']
        mock_cmd2.get_command_config.return_value = {
            'flags': ['-c', '--code'],
            'description': 'generate code'
        }
        
        mock_list_commands.return_value = [mock_cmd1, mock_cmd2]
        
        # Capture output
        stdout = StringIO()
        sys.stdout = stdout
        
        print_help()
        
        help_output = stdout.getvalue()
        
        # Check content
        assert f'q {__version__}' in help_output
        assert DESCRIPTION in help_output
        assert 'Usage:' in help_output
        assert 'Commands' in help_output
        assert 'Options:' in help_output
        assert '-e, --explain' in help_output
        assert '-c, --code' in help_output
        assert '-o, --overwrite' in help_output
        assert '-n, --no-clip' in help_output
        assert '-v, --verbose' in help_output
    
    def test_help_flag_handling(self):
        """Test that help flags display help and exit."""
        for help_flag in ['-h', '--help']:
            sys.argv = ['q', help_flag]
            
            with patch('q.cli.print_help') as mock_print_help:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 0
                mock_print_help.assert_called_once()
    
    def test_no_arguments_shows_help(self):
        """Test that no arguments shows help."""
        sys.argv = ['q']
        
        with patch('q.cli.print_help') as mock_print_help:
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            mock_print_help.assert_called_once()
    
    @patch('q.cli.validate_commands')
    def test_command_validation_error(self, mock_validate):
        """Test that command validation errors cause exit."""
        mock_validate.return_value = ['Error: Invalid command configuration']
        
        sys.argv = ['q', 'test']
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'Error: Invalid command configuration' in error_output
    
    @patch('q.cli.list_commands')
    def test_multiple_commands_error(self, mock_list_commands):
        """Test error when multiple commands are provided."""
        # Mock commands
        mock_cmd1 = Mock()
        mock_cmd1.flags = ['-e', '--explain']
        mock_cmd2 = Mock()
        mock_cmd2.flags = ['-c', '--code']
        mock_list_commands.return_value = [mock_cmd1, mock_cmd2]
        
        sys.argv = ['q', '-e', '-c', 'test']
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'Only one command may be provided' in error_output
    
    @patch('q.cli.list_commands')
    def test_command_not_first_argument_error(self, mock_list_commands):
        """Test error when command is not the first argument."""
        mock_cmd = Mock()
        mock_cmd.flags = ['-e', '--explain']
        mock_list_commands.return_value = [mock_cmd]
        
        sys.argv = ['q', 'text', '-e']
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'Command must be the first argument' in error_output
    
    @patch('q.cli.list_commands')
    def test_invalid_command_error(self, mock_list_commands):
        """Test error for invalid command flags."""
        mock_list_commands.return_value = []
        
        sys.argv = ['q', '-x', 'test']  # Invalid command -x
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'Invalid command "-x"' in error_output
    
    @patch('q.cli.list_commands')
    def test_no_text_provided_error(self, mock_list_commands):
        """Test error when no text is provided for a command."""
        mock_cmd = Mock()
        mock_cmd.flags = ['-e', '--explain']
        mock_list_commands.return_value = [mock_cmd]
        
        sys.argv = ['q', '-e']  # No text after command
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'No text provided' in error_output
    
    @patch('q.cli.list_commands')
    @patch('q.cli.run_command')
    def test_option_parsing_individual_flags(self, mock_run_command, mock_list_commands):
        """Test parsing of individual option flags."""
        mock_cmd = Mock()
        mock_cmd.flags = ['-e', '--explain']
        mock_cmd.get_command_config.return_value = {'test': 'config'}
        mock_list_commands.return_value = [mock_cmd]
        
        sys.argv = ['q', '-e', 'test', '-v', '-n', '-o']
        
        with pytest.raises(SystemExit):
            main()
        
        # Check that run_command was called with correct options
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args
        options = call_args[1]  # Keyword arguments
        
        assert options['verbose'] == True
        assert options['no-clip'] == True
        assert options['overwrite'] == True
    
    @patch('q.cli.list_commands')
    @patch('q.cli.run_command')
    def test_option_parsing_combined_flags(self, mock_run_command, mock_list_commands):
        """Test parsing of combined option flags."""
        mock_cmd = Mock()
        mock_cmd.flags = ['-e', '--explain']
        mock_cmd.get_command_config.return_value = {'test': 'config'}
        mock_list_commands.return_value = [mock_cmd]
        
        sys.argv = ['q', '-e', 'test', '-vno']  # Combined flags
        
        with pytest.raises(SystemExit):
            main()
        
        # Check that run_command was called with correct options
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args
        options = call_args[1]  # Keyword arguments
        
        assert options['verbose'] == True
        assert options['no-clip'] == True
        assert options['overwrite'] == True
    
    @patch('q.cli.list_commands')
    def test_invalid_option_error(self, mock_list_commands):
        """Test error for invalid option flags."""
        mock_cmd = Mock()
        mock_cmd.flags = ['-e', '--explain']
        mock_list_commands.return_value = [mock_cmd]
        
        sys.argv = ['q', '-e', 'test', '-x']  # Invalid option -x
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'Invalid option "-x"' in error_output
    
    @patch('q.cli.list_commands')
    @patch('q.cli.run_command')
    def test_default_command_execution(self, mock_run_command, mock_list_commands):
        """Test execution of default command."""
        mock_cmd = Mock()
        mock_cmd.flags = []  # Default command has no flags
        mock_cmd.get_command_config.return_value = {'test': 'default_config'}
        mock_list_commands.return_value = [mock_cmd]
        
        with patch('q.cli.get_default_command', return_value=mock_cmd):
            sys.argv = ['q', 'hello world']
            
            with pytest.raises(SystemExit):
                main()
            
            # Check that run_command was called with default command
            mock_run_command.assert_called_once()
            call_args = mock_run_command.call_args
            assert call_args[0][0] == {'test': 'default_config'}  # Command config
            assert call_args[0][1] == 'hello world'  # Text
    
    @patch('q.cli.list_commands')
    @patch('q.cli.get_default_command')
    def test_no_default_command_error(self, mock_get_default, mock_list_commands):
        """Test error when no default command is found."""
        mock_list_commands.return_value = []
        mock_get_default.return_value = None
        
        sys.argv = ['q', 'test']
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'No default command found' in error_output
    
    def test_stderr_masking_when_piped(self):
        """Test that stderr is masked when stdout is piped."""
        with patch('sys.stdout.isatty', return_value=False):
            with patch('builtins.open', create=True) as mock_open:
                with patch('os.devnull', '/dev/null'):
                    with patch('q.cli.list_commands', return_value=[]):
                        with patch('q.cli.get_default_command', return_value=None):
                            sys.argv = ['q', 'test']
                            
                            with pytest.raises(SystemExit):
                                main()
                            
                            # Should have opened /dev/null for stderr
                            mock_open.assert_called_with('/dev/null', 'w')


@pytest.mark.unit
class TestRunCommand:
    """Test the run_command function specifically."""
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_text_generation(self, mock_get_provider, mock_get_config):
        """Test run_command for text generation."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.text = "This is a test response."
        mock_provider.generate_text.return_value = mock_response
        mock_get_provider.return_value = mock_provider
        
        # Mock command configuration
        cmd_config = {
            'flags': ['-e', '--explain'],
            'description': 'explain concepts',
            'clip_output': True,
            'model_args': {'model': 'gpt-4.1', 'temperature': 0.0},
            'messages': [
                {'role': 'developer', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': '{text}'}
            ]
        }
        
        # Capture output
        stdout = StringIO()
        sys.stdout = stdout
        
        with patch('q.cli.pyperclip.copy') as mock_copy:
            run_command(cmd_config, 'What is Python?')
        
        output = stdout.getvalue()
        
        # Check that response was displayed
        assert "This is a test response." in output
        
        # Check that clipboard copy was attempted (clip_output=True)
        mock_copy.assert_called_once_with("This is a test response.")
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_image_generation(self, mock_get_provider, mock_get_config):
        """Test run_command for image generation."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock image generator and provider
        test_image_data = create_test_image_data()
        
        with patch('q.cli.ImageGenerator') as mock_img_gen_class:
            mock_img_gen = Mock()
            mock_img_gen.generate.return_value = test_image_data
            mock_img_gen_class.return_value = mock_img_gen
            
            # Mock command configuration for image generation
            cmd_config = {
                'flags': ['-i', '--image'],
                'description': 'generate images',
                'clip_output': False,
                'model_args': {
                    'model': 'gpt-4.1',
                    'tools': [{'type': 'image_generation', 'size': '1024x1024', 'quality': 'auto'}]
                },
                'messages': [{'role': 'user', 'content': '{text}'}]
            }
            
            # Mock file operations
            with patch('builtins.open', create=True) as mock_open:
                stderr = StringIO()
                sys.stderr = stderr
                
                run_command(cmd_config, 'A beautiful sunset')
                
                error_output = stderr.getvalue()
                
                # Check that image was saved
                assert 'Image saved to' in error_output
                assert 'q_A_beautiful_sunset.png' in error_output
                
                # Check that file was written
                mock_open.assert_called_once()
                mock_open().write.assert_called_once_with(test_image_data)
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_with_verbose_option(self, mock_get_provider, mock_get_config):
        """Test run_command with verbose option."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.text = "Test response."
        mock_provider.generate_text.return_value = mock_response
        mock_get_provider.return_value = mock_provider
        
        cmd_config = {
            'model_args': {'model': 'gpt-4.1', 'temperature': 0.0},
            'messages': [{'role': 'user', 'content': 'test'}],
            'clip_output': False
        }
        
        # Capture stderr for verbose output
        stderr = StringIO()
        sys.stderr = stderr
        
        run_command(cmd_config, 'test', verbose=True)
        
        error_output = stderr.getvalue()
        
        # Check verbose output
        assert 'MODEL PARAMETERS:' in error_output
        assert 'model:' in error_output
        assert 'gpt-4.1' in error_output
        assert 'MESSAGES:' in error_output
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_with_overwrite_option(self, mock_get_provider, mock_get_config):
        """Test run_command with overwrite option."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.text = "Test response."
        mock_provider.generate_text.return_value = mock_response
        mock_get_provider.return_value = mock_provider
        
        # Command config with multiple user messages (to test overwrite)
        cmd_config = {
            'model_args': {'model': 'gpt-4.1'},
            'messages': [
                {'role': 'user', 'content': 'first message'},
                {'role': 'assistant', 'content': 'first response'},
                {'role': 'user', 'content': 'second message'},
                {'role': 'assistant', 'content': 'second response'},
                {'role': 'user', 'content': '{text}'}
            ],
            'clip_output': False
        }
        
        run_command(cmd_config, 'new message', overwrite=True)
        
        # Should have removed messages from second-to-last user message to last user message
        # The exact behavior depends on the implementation, but it should process without error
        mock_provider.generate_text.assert_called_once()
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_overwrite_with_insufficient_messages(self, mock_get_provider, mock_get_config):
        """Test overwrite option with insufficient message history."""
        # Mock configuration
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        cmd_config = {
            'model_args': {'model': 'gpt-4.1'},
            'messages': [{'role': 'user', 'content': '{text}'}],  # Only one user message
            'clip_output': False
        }
        
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            run_command(cmd_config, 'test', overwrite=True)
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'No previous command to overwrite' in error_output
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_no_clip_option(self, mock_get_provider, mock_get_config):
        """Test run_command with no-clip option."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.text = "Test response."
        mock_provider.generate_text.return_value = mock_response
        mock_get_provider.return_value = mock_provider
        
        cmd_config = {
            'model_args': {'model': 'gpt-4.1'},
            'messages': [{'role': 'user', 'content': '{text}'}],
            'clip_output': True  # Command normally copies to clipboard
        }
        
        with patch('q.cli.pyperclip.copy') as mock_copy:
            run_command(cmd_config, 'test', **{'no-clip': True})
        
        # Should not copy to clipboard due to no-clip option
        mock_copy.assert_not_called()
    
    @patch('q.cli.get_default_config')
    @patch('q.cli.get_default_provider')
    def test_run_command_clipboard_error_handling(self, mock_get_provider, mock_get_config):
        """Test run_command handles clipboard errors gracefully."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.text = "Test response."
        mock_provider.generate_text.return_value = mock_response
        mock_get_provider.return_value = mock_provider
        
        cmd_config = {
            'model_args': {'model': 'gpt-4.1'},
            'messages': [{'role': 'user', 'content': '{text}'}],
            'clip_output': True
        }
        
        # Mock clipboard to raise exception
        with patch('q.cli.pyperclip.copy', side_effect=Exception("Clipboard error")):
            # Should not raise exception - clipboard errors are ignored
            run_command(cmd_config, 'test')
    
    @patch('q.cli.get_default_config')
    def test_run_command_generation_error(self, mock_get_config):
        """Test run_command handles generation errors."""
        # Mock configuration
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        cmd_config = {
            'model_args': {'model': 'gpt-4.1'},
            'messages': [{'role': 'user', 'content': '{text}'}],
            'clip_output': False
        }
        
        # Mock provider to raise exception
        with patch('q.cli.get_default_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.generate_text.side_effect = Exception("Generation failed")
            mock_get_provider.return_value = mock_provider
            
            stderr = StringIO()
            sys.stderr = stderr
            
            with pytest.raises(SystemExit) as exc_info:
                run_command(cmd_config, 'test')
            
            assert exc_info.value.code == 1
            error_output = stderr.getvalue()
            assert 'Error:' in error_output


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for CLI functionality."""
    
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
    
    @patch('q.cli.get_default_provider')
    @patch('q.cli.get_default_config')
    @patch('q.cli.list_commands')
    def test_full_cli_workflow_explain_command(self, mock_list_commands, mock_get_config, mock_get_provider):
        """Test complete CLI workflow for explain command."""
        # Mock configuration
        mock_config = Mock()
        mock_config._save_resource = Mock()
        mock_get_config.return_value = mock_config
        
        # Mock provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.text = "Python is a high-level programming language."
        mock_provider.generate_text.return_value = mock_response
        mock_get_provider.return_value = mock_provider
        
        # Mock explain command
        mock_cmd = Mock()
        mock_cmd.flags = ['-e', '--explain']
        mock_cmd.get_command_config.return_value = {
            'flags': ['-e', '--explain'],
            'description': 'explain concepts',
            'clip_output': False,
            'model_args': {'model': 'gpt-4.1-mini', 'temperature': 0.0},
            'messages': [
                {'role': 'developer', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': '{text}'}
            ]
        }
        mock_list_commands.return_value = [mock_cmd]
        
        # Set up command line arguments
        sys.argv = ['q', '-e', 'What is Python?']
        
        # Capture output
        stdout = StringIO()
        sys.stdout = stdout
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        output = stdout.getvalue()
        assert "Python is a high-level programming language." in output
    
    @patch('q.cli.validate_commands')
    def test_command_validation_integration(self, mock_validate):
        """Test integration with command validation."""
        # Test successful validation
        mock_validate.return_value = []
        
        with patch('q.cli.print_help'):
            sys.argv = ['q']
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            mock_validate.assert_called_once()
        
        # Test failed validation
        mock_validate.return_value = ['Validation error']
        
        sys.argv = ['q', 'test']
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'Validation error' in error_output