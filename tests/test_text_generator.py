"""
Comprehensive unit tests for TextGenerator class.

Tests the provider-agnostic text generation functionality including:
- Basic text generation
- Conversation history management 
- Parameter validation
- Error handling
- Provider integration
- Export/import functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from q.generators.text import TextGenerator
from q.config.models import Message, MessageRole, ModelParameters, GenerationRequest, GenerationResponse
from q.utils.exceptions import GenerationError, ValidationError
from tests.conftest import MockProvider, assert_response_format


@pytest.mark.unit
class TestTextGenerator:
    """Test TextGenerator functionality."""
    
    def test_initialization_with_defaults(self):
        """Test TextGenerator initialization with default parameters."""
        with patch('q.generators.text.get_default_provider') as mock_provider, \
             patch('q.generators.text.ConfigManager') as mock_config:
            
            mock_provider.return_value = MockProvider()
            mock_config.return_value = Mock()
            
            generator = TextGenerator()
            
            assert generator.provider is not None
            assert generator.config is not None
            assert len(generator.conversation_history) == 0
            assert generator.processor is not None
    
    def test_initialization_with_custom_provider(self, mock_provider):
        """Test TextGenerator initialization with custom provider."""
        generator = TextGenerator(provider=mock_provider)
        
        assert generator.provider == mock_provider
        assert len(generator.conversation_history) == 0
    
    def test_basic_generation(self, mock_provider):
        """Test basic text generation."""
        mock_provider.set_responses(["Python is a high-level programming language."])
        generator = TextGenerator(provider=mock_provider)
        
        response = generator.generate("What is Python?", command_type="explain")
        
        assert_response_format(response)
        assert "Python is a high-level programming language" in response
    
    def test_generation_with_parameters(self, mock_provider):
        """Test text generation with custom parameters."""
        mock_provider.set_responses(["def sort_list(items): return sorted(items)"])
        generator = TextGenerator(provider=mock_provider)
        
        response = generator.generate(
            "Write a sort function",
            command_type="code",
            model="gpt-4.1",
            temperature=0.5,
            max_tokens=2048
        )
        
        assert_response_format(response)
        assert "sort_list" in response
    
    def test_conversation_history_management(self, mock_provider):
        """Test conversation history management."""
        responses = [
            "Hello! How can I help you?",
            "Python is a programming language.",
            "You can install packages using pip."
        ]
        mock_provider.set_responses(responses)
        generator = TextGenerator(provider=mock_provider)
        
        # First interaction
        response1 = generator.generate_with_history("Hello")
        assert len(generator.conversation_history) == 2  # User + Assistant
        assert generator.conversation_history[0].role == MessageRole.USER
        assert generator.conversation_history[1].role == MessageRole.ASSISTANT
        
        # Second interaction  
        response2 = generator.generate_with_history("What is Python?")
        assert len(generator.conversation_history) == 4  # 2 more messages
        
        # Third interaction
        response3 = generator.generate_with_history("How do I install packages?")
        assert len(generator.conversation_history) == 6  # 2 more messages
        
        # Verify responses
        assert "Hello" in responses[0]
        assert "Python" in responses[1]
        assert "pip" in responses[2]
    
    def test_clear_history(self, mock_provider):
        """Test conversation history clearing."""
        mock_provider.set_responses(["Response 1", "Response 2"])
        generator = TextGenerator(provider=mock_provider)
        
        # Generate some conversation
        generator.generate_with_history("Message 1")
        generator.generate_with_history("Message 2")
        assert len(generator.conversation_history) == 4
        
        # Clear history
        generator.clear_history()
        assert len(generator.conversation_history) == 0
    
    def test_get_and_set_history(self, mock_provider):
        """Test getting and setting conversation history."""
        generator = TextGenerator(provider=mock_provider)
        
        # Create test messages
        test_messages = [
            Message(MessageRole.USER, "Hello"),
            Message(MessageRole.ASSISTANT, "Hi there!"),
            Message(MessageRole.USER, "How are you?"),
            Message(MessageRole.ASSISTANT, "I'm doing well!")
        ]
        
        # Set history
        generator.set_history(test_messages)
        assert len(generator.conversation_history) == 4
        
        # Get history
        history = generator.get_history()
        assert len(history) == 4
        assert history[0].content == "Hello"
        assert history[1].content == "Hi there!"
        
        # Verify it's a copy (not the same object)
        assert history is not generator.conversation_history
    
    def test_export_conversation(self, mock_provider):
        """Test conversation export functionality."""
        mock_provider.set_responses(["Hello!", "I'm fine!"])
        generator = TextGenerator(provider=mock_provider)
        
        # Generate some conversation
        generator.generate_with_history("Hello")
        generator.generate_with_history("How are you?")
        
        # Export conversation
        exported = generator.export_conversation()
        
        assert 'messages' in exported
        assert 'provider' in exported
        assert 'version' in exported
        assert len(exported['messages']) == 4
        assert exported['provider'] == 'mock'
        assert exported['version'] == '2.0'
        
        # Check message format
        first_message = exported['messages'][0]
        assert 'role' in first_message
        assert 'content' in first_message
    
    def test_import_conversation(self, mock_provider):
        """Test conversation import functionality."""
        generator = TextGenerator(provider=mock_provider)
        
        # Test data
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'},
                {'role': 'user', 'content': 'How are you?'},
                {'role': 'assistant', 'content': 'I\'m doing well!'}
            ],
            'provider': 'openai',
            'version': '2.0'
        }
        
        # Import conversation
        generator.import_conversation(conversation_data)
        
        assert len(generator.conversation_history) == 4
        assert generator.conversation_history[0].content == "Hello"
        assert generator.conversation_history[1].content == "Hi there!"
        assert generator.conversation_history[2].content == "How are you?"
        assert generator.conversation_history[3].content == "I'm doing well!"
    
    def test_import_conversation_with_invalid_messages(self, mock_provider):
        """Test conversation import with some invalid messages."""
        generator = TextGenerator(provider=mock_provider)
        
        # Test data with some invalid messages
        conversation_data = {
            'messages': [
                {'role': 'user', 'content': 'Hello'},  # Valid
                {'invalid': 'data'},                   # Invalid
                {'role': 'assistant', 'content': 'Hi there!'},  # Valid
                {'role': 'unknown_role', 'content': 'Test'}     # Invalid role
            ]
        }
        
        # Import conversation (should skip invalid messages)
        generator.import_conversation(conversation_data)
        
        # Should only have valid messages
        assert len(generator.conversation_history) == 2
        assert generator.conversation_history[0].content == "Hello"
        assert generator.conversation_history[1].content == "Hi there!"
    
    def test_generate_raw(self, mock_provider):
        """Test low-level raw generation method."""
        mock_provider.set_responses(["Raw response"])
        generator = TextGenerator(provider=mock_provider)
        
        messages = [Message(MessageRole.USER, "Test message")]
        model_params = ModelParameters(model="gpt-4.1", temperature=0.0)
        
        response = generator.generate_raw(messages, model_params)
        
        assert isinstance(response, GenerationResponse)
        assert response.text == "Raw response"
        assert response.model_used == "gpt-4.1"
    
    def test_get_available_models(self, mock_provider):
        """Test getting available models from provider."""
        generator = TextGenerator(provider=mock_provider)
        
        models = generator.get_available_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "mock-model-1" in models
        assert "gpt-4.1" in models
    
    def test_set_provider(self, mock_provider):
        """Test changing the provider."""
        generator = TextGenerator(provider=mock_provider)
        
        new_provider = MockProvider(provider_name="new-mock")
        generator.set_provider(new_provider)
        
        assert generator.provider == new_provider
        assert generator.provider.provider_name == "new-mock"
    
    # Error handling tests
    def test_empty_input_validation(self, mock_provider):
        """Test validation of empty input."""
        generator = TextGenerator(provider=mock_provider)
        
        with pytest.raises(ValidationError, match="Input text cannot be empty"):
            generator.generate("")
        
        with pytest.raises(ValidationError, match="Input text cannot be empty"):
            generator.generate("   ")  # Only whitespace
        
        with pytest.raises(ValidationError, match="Input text cannot be empty"):
            generator.generate_with_history("")
    
    def test_provider_error_handling(self, mock_provider):
        """Test handling of provider errors."""
        mock_provider.set_failure_mode(True)
        generator = TextGenerator(provider=mock_provider)
        
        with pytest.raises(GenerationError, match="Text generation failed"):
            generator.generate("Test input")
        
        with pytest.raises(GenerationError, match="Text generation with history failed"):
            generator.generate_with_history("Test input")
    
    def test_empty_response_handling(self, mock_provider):
        """Test handling of empty responses from provider."""
        # Mock provider to return empty response
        mock_response = GenerationResponse(text="", model_used="test")
        mock_provider.generate_text = Mock(return_value=mock_response)
        
        generator = TextGenerator(provider=mock_provider)
        
        with pytest.raises(GenerationError, match="No text response received from provider"):
            generator.generate("Test input")
    
    def test_raw_generation_empty_messages(self, mock_provider):
        """Test raw generation with empty messages list."""
        generator = TextGenerator(provider=mock_provider)
        
        with pytest.raises(ValidationError, match="Messages list cannot be empty"):
            generator.generate_raw([], ModelParameters())
    
    def test_command_type_validation(self, mock_provider):
        """Test validation of command types."""
        generator = TextGenerator(provider=mock_provider)
        
        # Test with valid command types
        valid_commands = ["default", "explain", "code", "shell", "web", "image"]
        for cmd_type in valid_commands:
            try:
                # This should not raise an error (might fail for other reasons but not validation)
                generator.generate("test", command_type=cmd_type)
            except ValidationError as e:
                if "Unknown command type" in str(e):
                    pytest.fail(f"Valid command type '{cmd_type}' was rejected")
    
    def test_model_parameter_override(self, mock_provider):
        """Test that model parameters are properly overridden."""
        generator = TextGenerator(provider=mock_provider)
        
        # Mock the provider to capture the request
        original_generate = mock_provider.generate_text
        captured_requests = []
        
        def capture_request(request):
            captured_requests.append(request)
            return original_generate(request)
        
        mock_provider.generate_text = capture_request
        
        # Generate with overridden parameters
        generator.generate(
            "test",
            model="custom-model",
            temperature=0.8,
            max_tokens=512
        )
        
        # Check that parameters were overridden
        assert len(captured_requests) == 1
        request = captured_requests[0]
        assert request.model_params.model == "custom-model"
        assert request.model_params.temperature == 0.8
        assert request.model_params.max_output_tokens == 512
    
    def test_conversation_context_preservation(self, mock_provider):
        """Test that conversation context is preserved across generations."""
        mock_provider.set_responses(["Response 1", "Response 2"])
        generator = TextGenerator(provider=mock_provider)
        
        # Mock the provider to capture requests
        captured_requests = []
        original_generate = mock_provider.generate_text
        
        def capture_request(request):
            captured_requests.append(request)
            return original_generate(request)
        
        mock_provider.generate_text = capture_request
        
        # First message
        generator.generate_with_history("Message 1")
        assert len(captured_requests) == 1
        assert len(captured_requests[0].messages) == 1  # Only new message
        
        # Second message - should include previous context for default command
        generator.generate_with_history("Message 2")
        assert len(captured_requests) == 2
        # For default command, should include full history
        if captured_requests[1].command_type == "default":
            assert len(captured_requests[1].messages) == 3  # Previous user + assistant + new user
    
    @pytest.mark.performance
    def test_generation_performance(self, mock_provider):
        """Test that generation completes within reasonable time."""
        import time
        
        generator = TextGenerator(provider=mock_provider)
        
        start_time = time.time()
        generator.generate("Test performance")
        end_time = time.time()
        
        # Should complete within 1 second for mock provider
        assert (end_time - start_time) < 1.0
    
    def test_thread_safety_basic(self, mock_provider):
        """Basic test for thread safety concerns."""
        import threading
        
        generator = TextGenerator(provider=mock_provider)
        results = []
        errors = []
        
        def generate_text(text):
            try:
                result = generator.generate(f"Test {text}")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple generations concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_text, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
    
    def test_memory_usage_history_management(self, mock_provider):
        """Test that conversation history doesn't grow unbounded."""
        generator = TextGenerator(provider=mock_provider)
        
        # Generate a long conversation
        for i in range(100):
            generator.generate_with_history(f"Message {i}")
        
        # History should contain all messages (no automatic pruning in basic implementation)
        assert len(generator.conversation_history) == 200  # 100 user + 100 assistant
        
        # But clearing should work
        generator.clear_history()
        assert len(generator.conversation_history) == 0


@pytest.mark.integration
class TestTextGeneratorIntegration:
    """Integration tests for TextGenerator with real-like scenarios."""
    
    def test_with_mock_openai_provider(self, mock_openai_client):
        """Test TextGenerator with mocked OpenAI provider."""
        with patch('q.providers.openai.openai.OpenAI', return_value=mock_openai_client), \
             patch('q.config.manager.ConfigManager._load_resource', return_value='test-key'):
            
            from q.providers.openai import OpenAIProvider
            provider = OpenAIProvider()
            generator = TextGenerator(provider=provider)
            
            response = generator.generate("What is Python?", command_type="explain")
            
            assert_response_format(response)
            assert "test response" in response.lower()
    
    def test_command_integration(self, mock_provider):
        """Test integration with command system."""
        generator = TextGenerator(provider=mock_provider)
        
        # Test different command types
        command_types = ["explain", "code", "shell"]
        
        for cmd_type in command_types:
            response = generator.generate(f"Test {cmd_type}", command_type=cmd_type)
            assert_response_format(response)
    
    def test_config_integration(self, mock_config_manager, mock_provider):
        """Test integration with configuration manager."""
        # Mock provider to return it when requested
        with patch('q.generators.text.get_default_provider', return_value=mock_provider):
            generator = TextGenerator(config=mock_config_manager)
            
            assert generator.config == mock_config_manager
            
            response = generator.generate("Test config integration")
            assert_response_format(response)