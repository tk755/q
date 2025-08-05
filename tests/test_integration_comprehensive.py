"""
Comprehensive integration tests for the Q library.

Tests end-to-end workflows including:
- Full CLI command execution
- Library usage patterns
- Cross-component integration
- Provider-generator-CLI integration
- Configuration management integration
- Real-world usage scenarios
"""

import pytest
import sys
import os
import tempfile
from io import StringIO
from unittest.mock import Mock, patch, MagicMock

from q import TextGenerator, ImageGenerator
from q.cli import main as cli_main
from q.providers.openai import OpenAIProvider
from q.config.manager import ConfigManager
from q.commands.registry import register_command, get_command
from tests.conftest import create_test_image_data


@pytest.mark.integration
class TestLibraryUsageIntegration:
    """Test library usage integration scenarios."""
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.config.manager.ConfigManager._load_resource')
    def test_basic_library_usage_workflow(self, mock_load_resource, mock_openai_class):
        """Test basic library usage workflow with TextGenerator."""
        # Mock configuration
        mock_load_resource.return_value = 'test-api-key'
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Python is a high-level programming language."
        mock_response.output = []
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Test TextGenerator usage
        generator = TextGenerator()
        response = generator.generate("What is Python?", command_type="explain")
        
        assert "Python is a high-level programming language" in response
        
        # Test conversation functionality
        response2 = generator.generate_with_history("How is it different from Java?")
        assert len(generator.conversation_history) == 2  # User + Assistant
        
        # Test conversation export/import
        exported = generator.export_conversation()
        assert 'messages' in exported
        assert 'provider' in exported
        
        new_generator = TextGenerator()
        new_generator.import_conversation(exported)
        assert len(new_generator.conversation_history) == 2
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.config.manager.ConfigManager._load_resource')
    def test_image_generation_library_workflow(self, mock_load_resource, mock_openai_class):
        """Test image generation library workflow."""
        # Mock configuration
        mock_load_resource.return_value = 'test-api-key'
        
        # Mock OpenAI client for image generation
        test_image_data = create_test_image_data()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Generated a beautiful sunset image"
        
        import base64
        mock_image_output = Mock()
        mock_image_output.type = 'image_generation_call'
        mock_image_output.result = base64.b64encode(test_image_data).decode()
        mock_response.output = [mock_image_output]
        
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Test ImageGenerator usage
        generator = ImageGenerator()
        image_data = generator.generate("A beautiful sunset")
        
        assert image_data == test_image_data
        
        # Test image saving
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            try:
                saved_path = generator.save_image(image_data, tmp_file.name)
                assert os.path.exists(saved_path)
                
                # Verify file contents
                with open(saved_path, 'rb') as f:
                    saved_data = f.read()
                assert saved_data == test_image_data
            finally:
                if os.path.exists(saved_path):
                    os.unlink(saved_path)
    
    def test_provider_switching_workflow(self, mock_provider):
        """Test switching providers in generators."""
        # Start with mock provider
        generator = TextGenerator(provider=mock_provider)
        mock_provider.set_responses(["Response from mock provider"])
        
        response1 = generator.generate("Test 1")
        assert "Response from mock provider" in response1
        
        # Switch to different provider
        new_provider = Mock()
        new_provider.generate_text.return_value = Mock(text="Response from new provider")
        new_provider.provider_name = "new_provider"
        
        generator.set_provider(new_provider)
        response2 = generator.generate("Test 2")
        assert "Response from new provider" in response2
    
    def test_configuration_integration_workflow(self, temp_config_file):
        """Test configuration management integration."""
        # Create config manager with test file
        config = ConfigManager(config_path=temp_config_file)
        
        # Test API key management
        config.set_api_key('openai', 'new-test-key')
        assert config.get_api_key('openai') == 'new-test-key'
        
        # Test preferences
        config.set_preference('default_model', 'gpt-4.1')
        assert config.get_preference('default_model') == 'gpt-4.1'
        
        # Test model defaults
        from q.config.models import ModelParameters
        new_params = ModelParameters(model='gpt-4.1', temperature=0.7)
        config.set_model_defaults('explain', new_params)
        
        # Test conversation management
        from q.config.models import Message, MessageRole
        messages = [
            Message(MessageRole.USER, "Hello"),
            Message(MessageRole.ASSISTANT, "Hi there!")
        ]
        config.save_conversation(messages)
        loaded_messages = config.load_conversation()
        
        assert len(loaded_messages) == 2
        assert loaded_messages[0].content == "Hello"
        assert loaded_messages[1].content == "Hi there!"
    
    def test_command_system_integration(self):
        """Test command system integration with generators."""
        from q.commands.explain import ExplainCommand
        from q.commands.code import CodeCommand
        
        # Test command registration and retrieval
        register_command(ExplainCommand)
        register_command(CodeCommand)
        
        explain_cmd = get_command('-e')
        code_cmd = get_command('-c')
        
        assert explain_cmd is not None
        assert code_cmd is not None
        
        # Test command message generation
        explain_messages = explain_cmd.get_messages("What is Python?")
        code_messages = code_cmd.get_messages("Sort a list")
        
        assert len(explain_messages) > 0
        assert len(code_messages) > 0
        
        # Test command model parameters
        explain_params = explain_cmd.get_model_params()
        code_params = code_cmd.get_model_params()
        
        assert explain_params.model == 'gpt-4.1-mini'
        assert code_params.model == 'gpt-4.1'  # Code uses full model
        
        # Test command configuration format
        explain_config = explain_cmd.get_command_config()
        assert 'flags' in explain_config
        assert 'messages' in explain_config
        assert 'model_args' in explain_config


@pytest.mark.integration
class TestCLIIntegrationComprehensive:
    """Comprehensive CLI integration tests."""
    
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
    def test_explain_command_full_workflow(self, mock_save, mock_load, mock_openai_class):
        """Test complete explain command workflow."""
        # Mock configuration
        def mock_load_side_effect(key, default):
            return {
                'openai_key': 'test-api-key',
                'model_args': {},
                'messages': [],
                'clip_output': False
            }.get(key, default)
        
        mock_load.side_effect = mock_load_side_effect
        
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Git rebase is a powerful feature that allows you to replay commits on top of another base tip."
        mock_response.output = []
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Set up CLI arguments
        sys.argv = ['q', '-e', 'explain git rebase']
        
        # Capture output
        stdout = StringIO()
        stderr = StringIO()
        sys.stdout = stdout
        sys.stderr = stderr
        
        with patch('q.cli.pyperclip.copy'):  # Mock clipboard
            with pytest.raises(SystemExit) as exc_info:
                cli_main()
        
        assert exc_info.value.code == 0
        output = stdout.getvalue()
        
        # Verify response was processed and displayed
        assert "Git rebase is a powerful feature" in output
        
        # Verify configuration was saved
        mock_save.assert_called()
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.config.manager.ConfigManager._load_resource')
    @patch('q.config.manager.ConfigManager._save_resource')
    def test_code_command_with_clipboard(self, mock_save, mock_load, mock_openai_class):
        """Test code command with clipboard functionality."""
        # Mock configuration
        def mock_load_side_effect(key, default):
            return {
                'openai_key': 'test-api-key',
                'model_args': {},
                'messages': [],
                'clip_output': True  # Code command copies to clipboard
            }.get(key, default)
        
        mock_load.side_effect = mock_load_side_effect
        
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "def sort_list(items):\n    return sorted(items)"
        mock_response.output = []
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Set up CLI arguments
        sys.argv = ['q', '-c', 'write a function to sort a list']
        
        # Capture output
        stdout = StringIO()
        stderr = StringIO()
        sys.stdout = stdout
        sys.stderr = stderr
        
        with patch('q.cli.pyperclip.copy') as mock_copy:
            with pytest.raises(SystemExit) as exc_info:
                cli_main()
        
        assert exc_info.value.code == 0
        output = stdout.getvalue()
        
        # Verify code was displayed
        assert "def sort_list(items):" in output
        
        # Verify clipboard copy was called
        mock_copy.assert_called_once()
        
        # Verify stderr message about clipboard
        error_output = stderr.getvalue()
        assert "copied to clipboard" in error_output.lower()
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.config.manager.ConfigManager._load_resource')
    @patch('q.config.manager.ConfigManager._save_resource')
    def test_image_command_full_workflow(self, mock_save, mock_load, mock_openai_class):
        """Test complete image generation workflow."""
        # Mock configuration
        def mock_load_side_effect(key, default):
            return {
                'openai_key': 'test-api-key',
                'model_args': {},
                'messages': [],
                'clip_output': False
            }.get(key, default)
        
        mock_load.side_effect = mock_load_side_effect
        
        # Mock OpenAI image response
        test_image_data = create_test_image_data()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Generated a beautiful mountain landscape"
        
        import base64
        mock_image_output = Mock()
        mock_image_output.type = 'image_generation_call'
        mock_image_output.result = base64.b64encode(test_image_data).decode()
        mock_response.output = [mock_image_output]
        
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Set up CLI arguments
        sys.argv = ['q', '-i', 'a beautiful mountain landscape']
        
        # Capture output
        stderr = StringIO()
        sys.stderr = stderr
        
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            with pytest.raises(SystemExit) as exc_info:
                cli_main()
        
        assert exc_info.value.code == 0
        error_output = stderr.getvalue()
        
        # Verify image was saved
        assert "Image saved to" in error_output
        assert "q_a_beautiful_mountain_landscape.png" in error_output
        
        # Verify file was written
        mock_open.assert_called_once()
        mock_open().write.assert_called_once_with(test_image_data)
    
    def test_verbose_option_workflow(self):
        """Test verbose option functionality."""
        # Mock provider and response
        with patch('q.cli.get_default_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_response = Mock()
            mock_response.text = "Test response for verbose mode."
            mock_provider.generate_text.return_value = mock_response
            mock_get_provider.return_value = mock_provider
            
            with patch('q.cli.get_default_config') as mock_get_config:
                mock_config = Mock()
                mock_config._save_resource = Mock()
                mock_get_config.return_value = mock_config
                
                # Set up CLI arguments with verbose flag
                sys.argv = ['q', '-e', 'test verbose mode', '-v']
                
                # Capture output
                stdout = StringIO()
                stderr = StringIO()
                sys.stdout = stdout
                sys.stderr = stderr
                
                with patch('q.cli.list_commands') as mock_list_commands:
                    mock_cmd = Mock()
                    mock_cmd.flags = ['-e', '--explain']
                    mock_cmd.get_command_config.return_value = {
                        'flags': ['-e', '--explain'],
                        'description': 'explain concepts',
                        'clip_output': False,
                        'model_args': {'model': 'gpt-4.1-mini', 'temperature': 0.0},
                        'messages': [{'role': 'user', 'content': '{text}'}]
                    }
                    mock_list_commands.return_value = [mock_cmd]
                    
                    with pytest.raises(SystemExit):
                        cli_main()
                
                error_output = stderr.getvalue()
                
                # Verify verbose output
                assert "MODEL PARAMETERS:" in error_output
                assert "MESSAGES:" in error_output
                assert "model:" in error_output
                assert "gpt-4.1-mini" in error_output
    
    def test_error_handling_workflow(self):
        """Test error handling in CLI workflow."""
        # Test invalid command
        sys.argv = ['q', '-x', 'invalid command']
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            cli_main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'Invalid command "-x"' in error_output
        
        # Test no text provided
        sys.argv = ['q', '-e']
        stderr = StringIO()
        sys.stderr = stderr
        
        with pytest.raises(SystemExit) as exc_info:
            cli_main()
        
        assert exc_info.value.code == 1
        error_output = stderr.getvalue()
        assert 'No text provided' in error_output
    
    def test_help_functionality(self):
        """Test help functionality."""
        # Test -h flag
        sys.argv = ['q', '-h']
        stdout = StringIO()
        sys.stdout = stdout
        
        with pytest.raises(SystemExit) as exc_info:
            cli_main()
        
        assert exc_info.value.code == 0
        help_output = stdout.getvalue()
        
        # Verify help content
        assert 'q 1.4.0' in help_output
        assert 'LLM-powered programming copilot' in help_output
        assert 'Usage:' in help_output
        assert 'Commands' in help_output
        assert 'Options:' in help_output
        
        # Test --help flag
        sys.argv = ['q', '--help']
        stdout = StringIO()
        sys.stdout = stdout
        
        with pytest.raises(SystemExit) as exc_info:
            cli_main()
        
        assert exc_info.value.code == 0
        help_output = stdout.getvalue()
        assert 'q 1.4.0' in help_output


@pytest.mark.integration  
class TestCrossComponentIntegration:
    """Test integration across different components."""
    
    def test_generator_provider_config_integration(self, mock_config_manager):
        """Test integration between generators, providers, and configuration."""
        from q.providers.factory import create_provider
        
        # Mock provider creation
        with patch('q.providers.factory.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.provider_name = "openai"
            mock_provider.supports_images = True
            mock_provider.supports_web_search = True
            mock_provider_class.return_value = mock_provider
            
            # Create provider through factory
            provider = create_provider('openai', config=mock_config_manager)
            
            # Create generators with provider and config
            text_gen = TextGenerator(provider=provider, config=mock_config_manager)
            image_gen = ImageGenerator(provider=provider, config=mock_config_manager)
            
            assert text_gen.provider == provider
            assert text_gen.config == mock_config_manager
            assert image_gen.provider == provider
            assert image_gen.config == mock_config_manager
    
    def test_command_generator_integration(self, mock_provider):
        """Test integration between commands and generators."""
        from q.commands.explain import ExplainCommand
        from q.commands.code import CodeCommand
        
        # Set up mock responses
        mock_provider.set_responses([
            "Python is a programming language.",
            "def quicksort(arr): return sorted(arr)"
        ])
        
        # Create generators
        text_gen = TextGenerator(provider=mock_provider)
        
        # Create commands
        explain_cmd = ExplainCommand()
        code_cmd = CodeCommand()
        
        # Test explain command integration
        response1 = text_gen.generate("What is Python?", command_type="explain")
        assert "Python is a programming language" in response1
        
        # Test code command integration
        response2 = text_gen.generate("Write a quicksort function", command_type="code")
        assert "quicksort" in response2
        
        # Verify command-specific model parameters were used
        explain_params = explain_cmd.get_model_params()
        code_params = code_cmd.get_model_params()
        
        assert explain_params.model == 'gpt-4.1-mini'
        assert code_params.model == 'gpt-4.1'
    
    def test_processing_integration_workflow(self):
        """Test integration with response processing."""
        from q.utils.processing import ResponseProcessor
        
        processor = ResponseProcessor()
        
        # Test processing of complex response
        complex_response = """Here's how to use git:

```bash
git add .
git commit -m "message"
```

Check the [Git documentation](https://git-scm.com/docs) for more info.

Use `git status` to check your status."""
        
        processed = processor.process_text_response(complex_response)
        
        # Verify all processing steps occurred
        assert "$ git add ." in processed  # Bash formatting
        assert "$ git commit -m \"message\"" in processed
        assert "Git documentation" in processed  # Link shortening
        assert "https://git-scm.com/docs" not in processed
        # Inline code should be colored (check for color codes)
        assert "\x1b[36mgit status\x1b[0m" in processed  # Cyan color codes
    
    def test_end_to_end_library_cli_consistency(self, mock_provider):
        """Test that library and CLI produce consistent results."""
        mock_provider.set_responses(["Consistent response for both library and CLI"])
        
        # Test library usage
        text_gen = TextGenerator(provider=mock_provider)
        library_response = text_gen.generate("Test input", command_type="explain")
        
        # Reset provider for CLI test
        mock_provider.set_responses(["Consistent response for both library and CLI"])
        
        # Test CLI usage (mocked)
        with patch('q.cli.get_default_provider', return_value=mock_provider):
            with patch('q.cli.get_default_config') as mock_get_config:
                mock_config = Mock()
                mock_config._save_resource = Mock()
                mock_get_config.return_value = mock_config
                
                # Simulate CLI run_command
                from q.cli import run_command
                from q.commands.explain import ExplainCommand
                
                explain_cmd = ExplainCommand()
                cmd_config = explain_cmd.get_command_config()
                
                stdout = StringIO()
                sys.stdout = stdout
                
                run_command(cmd_config, "Test input")
                cli_response = stdout.getvalue().strip()
        
        # Both should produce similar processed responses
        assert "Consistent response" in library_response
        assert "Consistent response" in cli_response
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.config.manager.ConfigManager._load_resource')
    def test_real_provider_integration(self, mock_load_resource, mock_openai_class):
        """Test integration with real provider implementation."""
        # Mock configuration
        mock_load_resource.return_value = 'test-api-key'
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Integration test response"
        mock_response.output = []
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Create real OpenAI provider
        provider = OpenAIProvider()
        
        # Test with TextGenerator
        text_gen = TextGenerator(provider=provider)
        response = text_gen.generate("Integration test", command_type="explain")
        
        assert "Integration test response" in response
        
        # Verify provider methods work
        assert provider.validate_connection() == True
        models = provider.get_available_models()
        assert isinstance(models, list)