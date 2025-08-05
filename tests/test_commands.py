"""
Tests for command system.
"""

import unittest
from q.commands import (
    ExplainCommand, CodeCommand, ShellCommand, ImageCommand, WebCommand, DefaultCommand
)
from q.commands.registry import register_command, get_command, list_commands, validate_commands
from q.config.models import Message, MessageRole, ModelParameters


class TestCommands(unittest.TestCase):
    """Test command implementations."""
    
    def test_explain_command(self):
        """Test ExplainCommand."""
        cmd = ExplainCommand()
        
        # Test properties
        self.assertEqual(cmd.flags, ['-e', '--explain'])
        self.assertIn('explain', cmd.description.lower())
        
        # Test messages
        messages = cmd.get_messages('what is python')
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, MessageRole.DEVELOPER)
        self.assertIn('programming assistant', messages[0].content.lower())
        self.assertEqual(messages[1].role, MessageRole.USER)
        self.assertIn('what is python', messages[1].content)
        
        # Test model parameters
        params = cmd.get_model_params()
        self.assertEqual(params.model, 'gpt-4.1-mini')
    
    def test_code_command(self):
        """Test CodeCommand."""
        cmd = CodeCommand()
        
        # Test properties
        self.assertEqual(cmd.flags, ['-c', '--code'])
        self.assertIn('code', cmd.description.lower())
        self.assertTrue(cmd.clip_output)  # Code command copies to clipboard
        
        # Test messages
        messages = cmd.get_messages('sort a list')
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, MessageRole.DEVELOPER)
        self.assertIn('coding assistant', messages[0].content.lower())
        self.assertEqual(messages[1].role, MessageRole.USER)
        self.assertIn('sort a list', messages[1].content)
        
        # Test model parameters
        params = cmd.get_model_params()
        self.assertEqual(params.model, 'gpt-4.1')  # Uses full model
    
    def test_shell_command(self):
        """Test ShellCommand."""
        cmd = ShellCommand()
        
        # Test properties
        self.assertEqual(cmd.flags, ['-s', '--shell'])
        self.assertIn('shell', cmd.description.lower())
        self.assertTrue(cmd.clip_output)  # Shell command copies to clipboard
        
        # Test messages
        messages = cmd.get_messages('find large files')
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, MessageRole.DEVELOPER)
        self.assertIn('command-line assistant', messages[0].content.lower())
        self.assertEqual(messages[1].role, MessageRole.USER)
        self.assertIn('find large files', messages[1].content)
    
    def test_image_command(self):
        """Test ImageCommand."""
        cmd = ImageCommand()
        
        # Test properties
        self.assertEqual(cmd.flags, ['-i', '--image'])
        self.assertIn('image', cmd.description.lower())
        
        # Test messages
        messages = cmd.get_messages('mountain landscape')
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, MessageRole.USER)
        self.assertIn('mountain landscape', messages[0].content)
        
        # Test model parameters (should have image generation tools)
        params = cmd.get_model_params()
        self.assertIsNotNone(params.tools)
        self.assertEqual(len(params.tools), 1)
        self.assertEqual(params.tools[0]['type'], 'image_generation')
    
    def test_web_command(self):
        """Test WebCommand."""
        cmd = WebCommand()
        
        # Test properties
        self.assertEqual(cmd.flags, ['-w', '--web'])
        self.assertIn('internet', cmd.description.lower())
        
        # Test messages
        messages = cmd.get_messages('current weather')
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, MessageRole.DEVELOPER)
        self.assertIn('real-time data', messages[0].content.lower())
        self.assertEqual(messages[1].role, MessageRole.USER)
        self.assertIn('current weather', messages[1].content)
        
        # Test model parameters (should have web search tools)
        params = cmd.get_model_params()
        self.assertIsNotNone(params.tools)
        self.assertEqual(len(params.tools), 1)
        self.assertEqual(params.tools[0]['type'], 'web_search_preview')
    
    def test_default_command(self):
        """Test DefaultCommand."""
        cmd = DefaultCommand()
        
        # Test properties
        self.assertEqual(cmd.flags, [])  # Default command has no flags
        self.assertIn('follow-up', cmd.description.lower())
    
    def test_command_config_format(self):
        """Test that commands produce correct config format for backward compatibility."""
        cmd = ExplainCommand()
        config = cmd.get_command_config()
        
        # Check required fields
        self.assertIn('flags', config)
        self.assertIn('description', config)
        self.assertIn('clip_output', config)
        self.assertIn('model_args', config)
        self.assertIn('messages', config)
        
        # Check format matches original q.py
        self.assertEqual(config['flags'], ['-e', '--explain'])
        self.assertIsInstance(config['model_args'], dict)
        self.assertIsInstance(config['messages'], list)


class TestCommandRegistry(unittest.TestCase):
    """Test command registry functionality."""
    
    def test_command_registration(self):
        """Test command registration and lookup."""
        # Commands should be auto-registered when module is imported
        explain_cmd = get_command('-e')
        self.assertIsInstance(explain_cmd, ExplainCommand)
        
        code_cmd = get_command('--code')
        self.assertIsInstance(code_cmd, CodeCommand)
    
    def test_list_commands(self):
        """Test listing all commands."""
        commands = list_commands()
        self.assertGreaterEqual(len(commands), 6)  # At least 6 commands (default + 5 others)
        
        # Check that we have expected command types
        command_types = [type(cmd).__name__ for cmd in commands]
        self.assertIn('DefaultCommand', command_types)
        self.assertIn('ExplainCommand', command_types)
        self.assertIn('CodeCommand', command_types)
    
    def test_validation(self):
        """Test command validation."""
        errors = validate_commands()
        self.assertEqual(len(errors), 0, f"Command validation failed: {errors}")


if __name__ == '__main__':
    unittest.main()