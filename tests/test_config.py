"""
Tests for configuration management.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open

from q.config.manager import ConfigManager
from q.config.models import UserPreferences, ModelParameters
from q.utils.exceptions import ConfigurationError


class TestConfigManager(unittest.TestCase):
    """Test ConfigManager functionality."""
    
    def setUp(self):
        """Set up test configuration with temporary file."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_resources.json')
        self.config = ConfigManager(config_path=self.config_path)
    
    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_backward_compatibility_functions(self):
        """Test backward compatibility with original q.py functions."""
        # Test _save_resource and _load_resource
        self.config._save_resource('test_key', 'test_value')
        value = self.config._load_resource('test_key', 'default')
        self.assertEqual(value, 'test_value')
        
        # Test default value
        default_value = self.config._load_resource('nonexistent', 'default')
        self.assertEqual(default_value, 'default')
    
    def test_api_key_management(self):
        """Test API key storage and retrieval."""
        # Test setting and getting API key
        self.config.set_api_key('openai', 'sk-test123')
        api_key = self.config.get_api_key('openai')
        self.assertEqual(api_key, 'sk-test123')
        
        # Test backward compatibility for OpenAI key
        legacy_key = self.config._load_resource('openai_key', None)
        self.assertEqual(legacy_key, 'sk-test123')
    
    def test_preferences(self):
        """Test user preferences management."""
        # Test setting and getting preferences
        self.config.set_preference('default_model', 'gpt-4.1')
        model = self.config.get_preference('default_model')
        self.assertEqual(model, 'gpt-4.1')
        
        # Test default value
        verbose = self.config.get_preference('verbose', False)
        self.assertEqual(verbose, False)
    
    def test_model_defaults(self):
        """Test model parameter defaults."""
        # Test getting default model parameters
        params = self.config.get_model_defaults()
        self.assertIsInstance(params, ModelParameters)
        self.assertEqual(params.model, 'gpt-4.1-mini')
        
        # Test setting model defaults
        new_params = ModelParameters(model='gpt-4.1', temperature=0.1)
        self.config.set_model_defaults('test', new_params)
        
        # Check that it was saved in backward compatible format
        stored_args = self.config._load_resource('model_args', {})
        self.assertEqual(stored_args['model'], 'gpt-4.1')
        self.assertEqual(stored_args['temperature'], 0.1)
    
    def test_conversation_management(self):
        """Test conversation history management."""
        from q.config.models import Message, MessageRole
        
        # Create test messages
        messages = [
            Message(MessageRole.USER, "Hello"),
            Message(MessageRole.ASSISTANT, "Hi there!")
        ]
        
        # Save and load conversation
        self.config.save_conversation(messages)
        loaded_messages = self.config.load_conversation()
        
        self.assertEqual(len(loaded_messages), 2)
        self.assertEqual(loaded_messages[0].content, "Hello")
        self.assertEqual(loaded_messages[1].content, "Hi there!")
    
    def test_file_operations(self):
        """Test file reading and writing operations."""
        # Test that config file is created
        self.config._save_resource('test', 'value')
        self.assertTrue(os.path.exists(self.config_path))
        
        # Test file content
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data['test'], 'value')
    
    def test_error_handling(self):
        """Test error handling for invalid configurations."""
        # Test with invalid JSON file
        with open(self.config_path, 'w') as f:
            f.write('invalid json')
        
        with self.assertRaises(ConfigurationError):
            ConfigManager(config_path=self.config_path)


if __name__ == '__main__':
    unittest.main()