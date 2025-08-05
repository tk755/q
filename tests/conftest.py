"""
Pytest configuration and fixtures for Q library tests.

Provides common fixtures and test utilities for all test modules.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

from q.providers.base import LLMProvider
from q.config.models import GenerationResponse, ModelParameters, Message, MessageRole
from q.config.manager import ConfigManager
from q.utils.exceptions import GenerationError, ValidationError


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, 
                 supports_images: bool = True, 
                 supports_web_search: bool = True,
                 provider_name: str = "mock"):
        self._supports_images = supports_images
        self._supports_web_search = supports_web_search
        self._provider_name = provider_name
        self._should_fail = False
        self._responses = []
        self._call_count = 0
        
    def set_responses(self, responses: List[str]):
        """Set predefined responses for testing."""
        self._responses = responses
        self._call_count = 0
    
    def set_failure_mode(self, should_fail: bool):
        """Set whether the provider should fail."""
        self._should_fail = should_fail
    
    def generate_text(self, request):
        if self._should_fail:
            raise GenerationError("Mock generation error")
        
        if self._responses and self._call_count < len(self._responses):
            response_text = self._responses[self._call_count]
            self._call_count += 1
        else:
            response_text = f"Mock response for: {request.messages[-1].content[:50]}..."
        
        return GenerationResponse(
            text=response_text,
            model_used=request.model_params.model,
            usage_stats={'tokens': 100},
            raw_response={'mock': True}
        )
    
    def generate_image(self, request):
        if self._should_fail:
            raise GenerationError("Mock image generation error")
        
        return GenerationResponse(
            text="Image generated",
            image_data=b"mock_image_data_12345",
            model_used=request.model_params.model,
            usage_stats={'tokens': 50},
            raw_response={'mock_image': True}
        )
    
    def validate_connection(self):
        return not self._should_fail
    
    def get_available_models(self):
        return ["mock-model-1", "mock-model-2", "gpt-4.1", "gpt-4.1-mini"]
    
    @property
    def supports_images(self):
        return self._supports_images
    
    @property
    def supports_web_search(self):
        return self._supports_web_search
    
    @property
    def provider_name(self):
        return self._provider_name


@pytest.fixture
def mock_provider():
    """Mock LLM provider fixture."""
    return MockProvider()


@pytest.fixture
def mock_provider_no_images():
    """Mock LLM provider that doesn't support images."""
    return MockProvider(supports_images=False)


@pytest.fixture
def temp_config_dir():
    """Temporary configuration directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def temp_config_file(temp_config_dir):
    """Temporary configuration file with test data."""
    config_path = os.path.join(temp_config_dir, 'resources.json')
    test_config = {
        'openai_key': 'test-api-key-12345',
        'model_args': {
            'model': 'gpt-4.1-mini',
            'temperature': 0.0,
            'max_output_tokens': 1024
        },
        'messages': [],
        'clip_output': False,
        'preferences': {
            'default_model': 'gpt-4.1-mini',
            'verbose': False
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(test_config, f)
    
    return config_path


@pytest.fixture
def mock_config_manager(temp_config_file):
    """Mock configuration manager with test data."""
    return ConfigManager(config_path=temp_config_file)


@pytest.fixture
def sample_messages():
    """Sample message history for testing."""
    return [
        Message(MessageRole.DEVELOPER, "You are a helpful programming assistant."),
        Message(MessageRole.USER, "Explain Python decorators"),
        Message(MessageRole.ASSISTANT, "Python decorators are a design pattern that allows...")
    ]


@pytest.fixture
def sample_model_params():
    """Sample model parameters for testing."""
    return ModelParameters(
        model='gpt-4.1-mini',
        temperature=0.0,
        max_output_tokens=1024
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = MagicMock()
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.output_text = "This is a test response from OpenAI"
    mock_response.output = []
    
    mock_client.responses.create.return_value = mock_response
    mock_client.models.list.return_value = MagicMock()
    
    return mock_client


@pytest.fixture
def mock_openai_image_client():
    """Mock OpenAI client with image generation support."""
    mock_client = MagicMock()
    
    # Mock image generation response
    mock_response = MagicMock()
    mock_response.output_text = "Generated image description"
    
    # Mock image output
    mock_image_output = MagicMock()
    mock_image_output.type = 'image_generation_call'
    mock_image_output.result = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="  # base64 encoded 1x1 PNG
    mock_response.output = [mock_image_output]
    
    mock_client.responses.create.return_value = mock_response
    mock_client.models.list.return_value = MagicMock()
    
    return mock_client


@pytest.fixture
def mock_clipboard():
    """Mock clipboard operations."""
    with patch('pyperclip.copy') as mock_copy:
        yield mock_copy


@pytest.fixture
def capture_output():
    """Capture stdout and stderr for testing CLI output."""
    import sys
    from io import StringIO
    
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture
    
    yield stdout_capture, stderr_capture
    
    sys.stdout = original_stdout
    sys.stderr = original_stderr


@pytest.fixture
def mock_file_system():
    """Mock file system operations for testing image saving."""
    with patch('builtins.open', create=True) as mock_open, \
         patch('os.path.abspath') as mock_abspath, \
         patch('os.path.exists') as mock_exists:
        
        mock_abspath.side_effect = lambda x: f"/mocked/path/{x}"
        mock_exists.return_value = True
        
        yield {
            'open': mock_open,
            'abspath': mock_abspath,
            'exists': mock_exists
        }


@pytest.fixture
def environment_variables():
    """Mock environment variables for testing."""
    env_vars = {
        'OPENAI_API_KEY': 'test-env-api-key',
        'Q_CONFIG_PATH': '/test/config/path'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def cli_args():
    """Helper fixture for mocking command line arguments."""
    def _mock_args(args_list):
        with patch('sys.argv', ['q'] + args_list):
            yield args_list
    
    return _mock_args


# Test data fixtures
@pytest.fixture
def test_prompts():
    """Common test prompts for various scenarios."""
    return {
        'simple': "What is Python?",
        'code': "Write a function to sort a list",
        'shell': "Find large files in current directory", 
        'explain': "Explain how git rebase works",
        'image': "A serene mountain landscape at sunset",
        'web': "Current weather in San Francisco",
        'complex': "Implement a binary search tree with insertion, deletion, and traversal methods",
        'empty': "",
        'long': "A" * 10000,  # Very long prompt
        'special_chars': "Test with special chars: !@#$%^&*()[]{}|\\:;\"'<>,.?/~`",
        'unicode': "Test with unicode: 🚀 ñáéíóú 中文 العربية"
    }


@pytest.fixture
def expected_responses():
    """Expected responses for test prompts."""
    return {
        'python_explanation': "Python is a high-level programming language...",
        'sort_function': "def sort_list(items):\n    return sorted(items)",
        'shell_command': "find . -type f -size +100M",
        'git_explanation': "Git rebase is a way to integrate changes...",
        'error_message': "Error: Invalid input provided",
        'image_saved': "Image saved to q_mountain_landscape.png"
    }


@pytest.fixture
def performance_benchmarks():
    """Performance benchmark thresholds."""
    return {
        'max_response_time': 5.0,  # seconds
        'max_memory_usage': 100,   # MB
        'max_file_size': 10,       # MB for generated files
        'min_throughput': 1.0      # requests per second
    }


# Utility functions for tests
def create_test_image_data():
    """Create test image data (minimal PNG)."""
    import base64
    # 1x1 pixel transparent PNG
    png_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    return base64.b64decode(png_data)


def create_test_conversation():
    """Create test conversation history."""
    return [
        {'role': 'user', 'content': 'Hello'},
        {'role': 'assistant', 'content': 'Hi! How can I help you?'},
        {'role': 'user', 'content': 'Explain Python'},
        {'role': 'assistant', 'content': 'Python is a programming language...'}
    ]


def assert_response_format(response_text: str):
    """Assert that response follows expected format."""
    assert isinstance(response_text, str)
    assert len(response_text) > 0
    assert not response_text.startswith('Error:')


def assert_valid_image_data(image_data: bytes):
    """Assert that image data is valid."""
    assert isinstance(image_data, bytes)
    assert len(image_data) > 0
    # Check for PNG header
    assert image_data.startswith(b'\x89PNG')


# Marks for organizing tests
pytestmark = pytest.mark.filterwarnings("ignore:.*:DeprecationWarning")