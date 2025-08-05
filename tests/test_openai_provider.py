"""
Comprehensive unit tests for OpenAI provider implementation.

Tests the OpenAI provider functionality including:
- Client initialization and authentication
- Text generation
- Image generation
- Error handling
- API key management
- Connection validation
- Model listing
"""

import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
import openai

from q.providers.openai import OpenAIProvider
from q.config.models import GenerationRequest, GenerationResponse, Message, MessageRole, ModelParameters
from q.utils.exceptions import GenerationError, AuthenticationError, RateLimitError
from tests.conftest import create_test_image_data


@pytest.mark.unit
class TestOpenAIProvider:
    """Test OpenAI provider functionality."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        provider = OpenAIProvider(api_key="test-key-123")
        
        assert provider._api_key == "test-key-123"
        assert provider._client is None  # Client is lazy-loaded
        assert provider.provider_name == "openai"
        assert provider.supports_images == True
        assert provider.supports_web_search == True
    
    def test_initialization_without_api_key(self):
        """Test provider initialization without API key."""
        provider = OpenAIProvider()
        
        assert provider._api_key is None
        assert provider._client is None
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.providers.openai.get_default_config')
    def test_get_client_with_stored_key(self, mock_get_config, mock_openai_class):
        """Test client creation with stored API key."""
        # Mock config
        mock_config = Mock()
        mock_config._load_resource.return_value = 'stored-api-key'
        mock_get_config.return_value = mock_config
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider()
        client = provider._get_client()
        
        assert client == mock_client
        mock_openai_class.assert_called_once_with(api_key='stored-api-key')
        mock_client.models.list.assert_called_once()
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.providers.openai.get_default_config')
    @patch('q.providers.openai.getpass.getpass')
    @patch('q.providers.openai.cprint')
    def test_get_client_prompt_for_key(self, mock_cprint, mock_getpass, mock_get_config, mock_openai_class):
        """Test client creation when API key needs to be prompted."""
        # Mock config
        mock_config = Mock()
        mock_config._load_resource.return_value = None  # No stored key
        mock_get_config.return_value = mock_config
        
        # Mock user input
        mock_getpass.return_value = 'user-entered-key'
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider()
        client = provider._get_client()
        
        assert client == mock_client
        mock_cprint.assert_called()  # Should prompt user
        mock_getpass.assert_called_once()
        mock_config._save_resource.assert_called_with('openai_key', 'user-entered-key')
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.providers.openai.get_default_config')
    @patch('q.providers.openai.getpass.getpass')
    @patch('q.providers.openai.cprint')
    def test_get_client_invalid_key_retry(self, mock_cprint, mock_getpass, mock_get_config, mock_openai_class):
        """Test client creation with invalid key that requires retry."""
        # Mock config
        mock_config = Mock()
        mock_config._load_resource.return_value = 'invalid-key'
        mock_get_config.return_value = mock_config
        
        # Mock user input for retry
        mock_getpass.return_value = 'valid-key'
        
        # Mock OpenAI client - first call fails, second succeeds
        mock_client_invalid = Mock()
        mock_client_invalid.models.list.side_effect = openai.APIError("Invalid API key")
        
        mock_client_valid = Mock()
        mock_client_valid.models.list.return_value = Mock()
        
        mock_openai_class.side_effect = [mock_client_invalid, mock_client_valid]
        
        provider = OpenAIProvider()
        client = provider._get_client()
        
        assert client == mock_client_valid
        assert mock_getpass.call_count == 1  # Should prompt for new key
        assert mock_config._save_resource.call_count == 1  # Should save new key
    
    def test_prompt_model_text_generation(self, mock_openai_client):
        """Test the internal _prompt_model method for text generation."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        model_args = {'model': 'gpt-4.1', 'temperature': 0.0}
        messages = [{'role': 'user', 'content': 'Hello'}]
        
        text_response, image_response = provider._prompt_model(model_args, messages)
        
        assert text_response == "This is a test response from OpenAI"
        assert image_response is None
        mock_openai_client.responses.create.assert_called_once_with(
            input=messages,
            **model_args
        )
    
    def test_prompt_model_image_generation(self, mock_openai_image_client):
        """Test the internal _prompt_model method for image generation."""
        provider = OpenAIProvider()
        provider._client = mock_openai_image_client
        
        model_args = {'model': 'gpt-4.1', 'tools': [{'type': 'image_generation'}]}
        messages = [{'role': 'user', 'content': 'Generate a sunset image'}]
        
        text_response, image_response = provider._prompt_model(model_args, messages)
        
        assert text_response == "Generated image description"
        assert image_response is not None
        assert image_response.type == 'image_generation_call'
    
    def test_generate_text_success(self, mock_openai_client):
        """Test successful text generation."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Create test request
        messages = [Message(MessageRole.USER, "What is Python?")]
        model_params = ModelParameters(model='gpt-4.1', temperature=0.0)
        request = GenerationRequest(
            messages=messages,
            model_params=model_params,
            command_type="explain"
        )
        
        response = provider.generate_text(request)
        
        assert isinstance(response, GenerationResponse)
        assert response.text == "This is a test response from OpenAI"
        assert response.model_used == 'gpt-4.1'
        assert response.image_data is None
    
    def test_generate_image_success(self, mock_openai_image_client):
        """Test successful image generation."""
        provider = OpenAIProvider()
        provider._client = mock_openai_image_client
        
        # Create test request with image generation tools
        messages = [Message(MessageRole.USER, "Generate a sunset image")]
        model_params = ModelParameters(
            model='gpt-4.1',
            tools=[{'type': 'image_generation', 'size': '1024x1024'}]
        )
        request = GenerationRequest(
            messages=messages,
            model_params=model_params,
            command_type="image"
        )
        
        response = provider.generate_image(request)
        
        assert isinstance(response, GenerationResponse)
        assert response.text == "Generated image description"
        assert response.image_data is not None
        assert len(response.image_data) > 0  # Should contain decoded image data
    
    def test_generate_image_without_tools(self, mock_openai_client):
        """Test image generation without required tools raises error."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Create request without image generation tools
        messages = [Message(MessageRole.USER, "Generate an image")]
        model_params = ModelParameters(model='gpt-4.1')
        request = GenerationRequest(
            messages=messages,
            model_params=model_params,
            command_type="image"
        )
        
        with pytest.raises(ValidationError, match="Image generation requires image_generation tool"):
            provider.generate_image(request)
    
    def test_api_error_handling_authentication(self, mock_openai_client):
        """Test handling of authentication errors."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock authentication error
        mock_openai_client.responses.create.side_effect = openai.APIError("authentication failed")
        
        messages = [Message(MessageRole.USER, "Test")]
        model_params = ModelParameters(model='gpt-4.1')
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        with pytest.raises(AuthenticationError, match="OpenAI API authentication failed"):
            provider.generate_text(request)
    
    def test_api_error_handling_rate_limit(self, mock_openai_client):
        """Test handling of rate limit errors."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock rate limit error
        mock_openai_client.responses.create.side_effect = openai.APIError("rate_limit exceeded")
        
        messages = [Message(MessageRole.USER, "Test")]
        model_params = ModelParameters(model='gpt-4.1')
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        with pytest.raises(RateLimitError, match="OpenAI API rate limit exceeded"):
            provider.generate_text(request)
    
    def test_api_error_handling_quota(self, mock_openai_client):
        """Test handling of quota errors."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock quota error
        mock_openai_client.responses.create.side_effect = openai.APIError("quota exceeded")
        
        messages = [Message(MessageRole.USER, "Test")]
        model_params = ModelParameters(model='gpt-4.1')
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        with pytest.raises(RateLimitError, match="OpenAI API rate limit exceeded"):
            provider.generate_text(request)
    
    def test_api_error_handling_generic(self, mock_openai_client):
        """Test handling of generic API errors."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock generic error
        mock_openai_client.responses.create.side_effect = openai.APIError("Unknown error")
        
        messages = [Message(MessageRole.USER, "Test")]
        model_params = ModelParameters(model='gpt-4.1')
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        with pytest.raises(GenerationError, match="OpenAI API error"):
            provider.generate_text(request)
    
    def test_unexpected_error_handling(self, mock_openai_client):
        """Test handling of unexpected errors."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock unexpected error
        mock_openai_client.responses.create.side_effect = Exception("Unexpected error")
        
        messages = [Message(MessageRole.USER, "Test")]
        model_params = ModelParameters(model='gpt-4.1')
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        with pytest.raises(GenerationError, match="Unexpected error during generation"):
            provider.generate_text(request)
    
    def test_validate_connection_success(self, mock_openai_client):
        """Test successful connection validation."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        assert provider.validate_connection() == True
        mock_openai_client.models.list.assert_called()
    
    def test_validate_connection_failure(self, mock_openai_client):
        """Test failed connection validation."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock connection failure
        mock_openai_client.models.list.side_effect = Exception("Connection failed")
        
        assert provider.validate_connection() == False
    
    def test_get_available_models_success(self, mock_openai_client):
        """Test getting available models successfully."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock model list response
        mock_model1 = Mock()
        mock_model1.id = "gpt-4.1"
        mock_model2 = Mock()
        mock_model2.id = "gpt-4.1-mini"
        
        mock_response = Mock()
        mock_response.data = [mock_model1, mock_model2]
        mock_openai_client.models.list.return_value = mock_response
        
        models = provider.get_available_models()
        
        assert models == ["gpt-4.1", "gpt-4.1-mini"]
    
    def test_get_available_models_fallback(self, mock_openai_client):
        """Test getting available models with fallback on error."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock error in models.list
        mock_openai_client.models.list.side_effect = Exception("API error")
        
        models = provider.get_available_models()
        
        # Should return fallback list
        expected_models = ["gpt-4.1", "gpt-4.1-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        assert models == expected_models
    
    def test_message_format_conversion(self, mock_openai_client):
        """Test that messages are properly converted to dict format."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock the _prompt_model to capture arguments
        with patch.object(provider, '_prompt_model') as mock_prompt:
            mock_prompt.return_value = ("response", None)
            
            messages = [
                Message(MessageRole.USER, "Hello"),
                Message(MessageRole.ASSISTANT, "Hi there!")
            ]
            model_params = ModelParameters(model='gpt-4.1')
            request = GenerationRequest(messages=messages, model_params=model_params)
            
            provider.generate_text(request)
            
            # Check that _prompt_model was called with dict messages
            call_args = mock_prompt.call_args
            message_dicts = call_args[0][1]  # Second argument is messages
            
            assert len(message_dicts) == 2
            assert message_dicts[0]['role'] == 'user'
            assert message_dicts[0]['content'] == 'Hello'
            assert message_dicts[1]['role'] == 'assistant'
            assert message_dicts[1]['content'] == 'Hi there!'
    
    def test_model_params_conversion(self, mock_openai_client):
        """Test that model parameters are properly converted to dict format."""
        provider = OpenAIProvider()
        provider._client = mock_openai_client
        
        # Mock the _prompt_model to capture arguments
        with patch.object(provider, '_prompt_model') as mock_prompt:
            mock_prompt.return_value = ("response", None)
            
            messages = [Message(MessageRole.USER, "Test")]
            model_params = ModelParameters(
                model='gpt-4.1',
                temperature=0.5,
                max_output_tokens=2048,
                tools=[{'type': 'web_search'}]
            )
            request = GenerationRequest(messages=messages, model_params=model_params)
            
            provider.generate_text(request)
            
            # Check that _prompt_model was called with dict model args
            call_args = mock_prompt.call_args
            model_args = call_args[0][0]  # First argument is model_args
            
            assert model_args['model'] == 'gpt-4.1'
            assert model_args['temperature'] == 0.5
            assert model_args['max_output_tokens'] == 2048
            assert model_args['tools'] == [{'type': 'web_search'}]
    
    def test_image_data_decoding(self, mock_openai_image_client):
        """Test that image data is properly decoded from base64."""
        provider = OpenAIProvider()
        provider._client = mock_openai_image_client
        
        # Create test request
        messages = [Message(MessageRole.USER, "Generate an image")]
        model_params = ModelParameters(
            model='gpt-4.1',
            tools=[{'type': 'image_generation'}]
        )
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        response = provider.generate_image(request)
        
        # Check that image data was decoded
        assert response.image_data is not None
        assert isinstance(response.image_data, bytes)
        
        # The mock returns a valid base64 encoded 1x1 PNG
        # Check that it was properly decoded
        assert len(response.image_data) > 0
    
    def test_client_caching(self, mock_openai_client):
        """Test that OpenAI client is cached after first creation."""
        with patch('q.providers.openai.openai.OpenAI', return_value=mock_openai_client) as mock_openai_class:
            provider = OpenAIProvider(api_key="test-key")
            
            # First call should create client
            client1 = provider._get_client()
            assert mock_openai_class.call_count == 1
            
            # Second call should return cached client
            client2 = provider._get_client()
            assert mock_openai_class.call_count == 1  # No additional calls
            
            assert client1 == client2 == mock_openai_client


@pytest.mark.integration
class TestOpenAIProviderIntegration:
    """Integration tests for OpenAI provider."""
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.providers.openai.get_default_config')
    def test_full_text_generation_workflow(self, mock_get_config, mock_openai_class):
        """Test complete text generation workflow."""
        # Setup mocks
        mock_config = Mock()
        mock_config._load_resource.return_value = 'test-api-key'
        mock_get_config.return_value = mock_config
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Python is a programming language."
        mock_response.output = []
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Create provider and generate text
        provider = OpenAIProvider()
        
        messages = [Message(MessageRole.USER, "What is Python?")]
        model_params = ModelParameters(model='gpt-4.1', temperature=0.0)
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        response = provider.generate_text(request)
        
        # Verify complete workflow
        assert response.text == "Python is a programming language."
        assert response.model_used == 'gpt-4.1'
        mock_client.responses.create.assert_called_once()
    
    @patch('q.providers.openai.openai.OpenAI')
    @patch('q.providers.openai.get_default_config')
    def test_full_image_generation_workflow(self, mock_get_config, mock_openai_class):
        """Test complete image generation workflow."""
        # Setup mocks
        mock_config = Mock()
        mock_config._load_resource.return_value = 'test-api-key'
        mock_get_config.return_value = mock_config
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.output_text = "Generated a beautiful sunset"
        
        # Mock image output with valid base64 data
        test_image_data = create_test_image_data()
        encoded_data = base64.b64encode(test_image_data).decode()
        
        mock_image_output = Mock()
        mock_image_output.type = 'image_generation_call'
        mock_image_output.result = encoded_data
        mock_response.output = [mock_image_output]
        
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = Mock()
        mock_openai_class.return_value = mock_client
        
        # Create provider and generate image
        provider = OpenAIProvider()
        
        messages = [Message(MessageRole.USER, "Generate a sunset image")]
        model_params = ModelParameters(
            model='gpt-4.1',
            tools=[{'type': 'image_generation', 'size': '1024x1024'}]
        )
        request = GenerationRequest(messages=messages, model_params=model_params)
        
        response = provider.generate_image(request)
        
        # Verify complete workflow
        assert response.text == "Generated a beautiful sunset"
        assert response.image_data == test_image_data
        assert response.model_used == 'gpt-4.1'
        mock_client.responses.create.assert_called_once()
    
    def test_error_propagation(self):
        """Test that errors are properly propagated through the stack."""
        provider = OpenAIProvider(api_key="invalid-key")
        
        with patch.object(provider, '_get_client') as mock_get_client:
            mock_get_client.side_effect = AuthenticationError("Invalid API key")
            
            messages = [Message(MessageRole.USER, "Test")]
            model_params = ModelParameters(model='gpt-4.1')
            request = GenerationRequest(messages=messages, model_params=model_params)
            
            # Error should propagate up
            with pytest.raises(AuthenticationError):
                provider.generate_text(request)