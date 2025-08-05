"""
Integration tests for the Q library.

Tests the full integration between components while mocking external dependencies.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import io
from q import TextGenerator, ImageGenerator
from q.cli import main as cli_main
from q.providers.factory import get_provider
from q.config.manager import ConfigManager


class TestLibraryIntegration(unittest.TestCase):
    """Test library usage integration."""
    
    @patch('q.providers.openai.openai.OpenAI')
    def test_basic_library_usage(self, mock_openai_client):
        """Test basic library usage scenario."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.output_text = "Python is a programming language."
        mock_response.output = []
        
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # Test TextGenerator
        with patch('q.config.manager.ConfigManager._load_resource') as mock_load:
            mock_load.return_value = 'mock-api-key'
            
            generator = TextGenerator()
            response = generator.generate("What is Python?", command_type="explain")
            
            self.assertIsInstance(response, str)
            self.assertIn("Python", response)
    
    @patch('q.providers.openai.openai.OpenAI')
    def test_conversation_flow(self, mock_openai_client):
        """Test conversation flow with history."""
        # Mock OpenAI responses
        responses = [
            "Hello! How can I help you?",
            "Python is a programming language.",
            "You can install packages using pip."
        ]
        
        mock_client = MagicMock()
        mock_client.models.list.return_value = MagicMock()
        mock_openai_client.return_value = mock_client
        
        with patch('q.config.manager.ConfigManager._load_resource') as mock_load:
            mock_load.return_value = 'mock-api-key'
            
            generator = TextGenerator()
            
            # Simulate conversation
            for i, expected_response in enumerate(responses):
                mock_response = MagicMock()
                mock_response.output_text = expected_response
                mock_response.output = []
                mock_client.responses.create.return_value = mock_response
                
                if i == 0:
                    response = generator.generate_with_history("Hello")
                elif i == 1:
                    response = generator.generate_with_history("What is Python?")
                else:
                    response = generator.generate_with_history("How do I install packages?")
                
                self.assertEqual(response, expected_response)
            
            # Check conversation history
            history = generator.get_history()
            self.assertEqual(len(history), 6)  # 3 user + 3 assistant messages


class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration with mocked dependencies."""
    
    def setUp(self):
        """Set up for CLI tests."""
        self.original_argv = sys.argv
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def tearDown(self):
        """Clean up after CLI tests."""
        sys.argv = self.original_argv
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    def test_help_output(self):
        """Test help output generation."""
        sys.argv = ['q', '--help']
        stdout = io.StringIO()
        sys.stdout = stdout
        
        with self.assertRaises(SystemExit) as cm:
            cli_main()
        
        self.assertEqual(cm.exception.code, 0)
        help_output = stdout.getvalue()
        
        # Check help content
        self.assertIn('q 1.4.0', help_output)
        self.assertIn('LLM-powered programming copilot', help_output)
        self.assertIn('Commands', help_output)
        self.assertIn('-e, --explain', help_output)
        self.assertIn('-c, --code', help_output)
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.config.manager.ConfigManager._load_resource')
    @patch('q.config.manager.ConfigManager._save_resource')
    def test_explain_command_cli(self, mock_save, mock_load, mock_openai_client):
        """Test explain command through CLI."""
        # Mock configuration
        mock_load.side_effect = lambda key, default: {
            'openai_key': 'mock-api-key',
            'model_args': {},
            'clip_output': False,
            'messages': []
        }.get(key, default)
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.output_text = "Git rebase replays commits on top of another base tip."
        mock_response.output = []
        
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # Capture output
        sys.argv = ['q', '-e', 'git rebase']
        stdout = io.StringIO()
        stderr = io.StringIO()
        sys.stdout = stdout
        sys.stderr = stderr
        
        # Mock clipboard to avoid errors
        with patch('q.cli.pyperclip.copy'):
            with self.assertRaises(SystemExit) as cm:
                cli_main()
        
        self.assertEqual(cm.exception.code, 0)
        output = stdout.getvalue()
        
        # Check that response was processed and displayed
        self.assertIn("Git rebase", output)
    
    def test_invalid_command_error(self):
        """Test error handling for invalid commands."""
        sys.argv = ['q', '-x', 'test']  # Invalid command
        stderr = io.StringIO()
        sys.stderr = stderr
        
        with self.assertRaises(SystemExit) as cm:
            cli_main()
        
        self.assertEqual(cm.exception.code, 1)
        error_output = stderr.getvalue()
        self.assertIn('Invalid command', error_output)
    
    def test_no_text_error(self):
        """Test error handling when no text is provided."""
        sys.argv = ['q', '-e']  # Command without text
        stderr = io.StringIO()
        sys.stderr = stderr
        
        with self.assertRaises(SystemExit) as cm:
            cli_main()
        
        self.assertEqual(cm.exception.code, 1)
        error_output = stderr.getvalue()
        self.assertIn('No text provided', error_output)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with original q.py behavior."""
    
    @patch('q.config.manager.ConfigManager._load_resource')
    @patch('q.config.manager.ConfigManager._save_resource')
    def test_resource_functions_compatibility(self, mock_save, mock_load):
        """Test that resource functions work like original q.py."""
        from q.config.manager import _load_resource, _save_resource
        
        mock_load.return_value = 'test_value'
        
        # Test loading
        value = _load_resource('test_key', 'default')
        mock_load.assert_called_with('test_key', 'default')
        
        # Test saving
        _save_resource('test_key', 'new_value')
        mock_save.assert_called_with('test_key', 'new_value')
    
    def test_command_config_format(self):
        """Test that command configurations match original format."""
        from q.commands import ExplainCommand
        
        cmd = ExplainCommand()
        config = cmd.get_command_config()
        
        # Check all required fields from original COMMANDS format
        required_fields = ['flags', 'description', 'clip_output', 'model_args', 'messages']
        for field in required_fields:
            self.assertIn(field, config)
        
        # Check specific formats
        self.assertIsInstance(config['flags'], list)
        self.assertIsInstance(config['model_args'], dict)
        self.assertIsInstance(config['messages'], list)
        self.assertIsInstance(config['clip_output'], bool)
    
    def test_message_format_compatibility(self):
        """Test that message formats are compatible."""
        from q.commands import DefaultCommand
        from q.config.models import Message, MessageRole
        
        cmd = DefaultCommand()
        
        # Mock stored messages in old format
        with patch('q.config.manager.ConfigManager._load_resource') as mock_load:
            mock_load.return_value = [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'}
            ]
            
            messages = cmd.get_messages('How are you?')
            
            # Should include history plus new message
            self.assertGreaterEqual(len(messages), 3)
            
            # New message should be at the end
            self.assertEqual(messages[-1].content, 'How are you?')
            self.assertEqual(messages[-1].role, MessageRole.USER)


if __name__ == '__main__':
    unittest.main()