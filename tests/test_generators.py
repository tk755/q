"""
Tests for generator classes.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from q.generators.text import TextGenerator
from q.generators.image import ImageGenerator
from q.providers.base import LLMProvider
from q.config.models import GenerationResponse, ModelParameters
from q.utils.exceptions import GenerationError, ValidationError


class MockProvider(LLMProvider):
    """Mock provider for testing."""
    
    def __init__(self):
        self.supports_images = True
        self.supports_web_search = True
        self.provider_name = "mock"
    
    def generate_text(self, request):
        return GenerationResponse(
            text="Mock response text",
            model_used="mock-model"
        )
    
    def generate_image(self, request):
        return GenerationResponse(
            image_data=b"mock_image_data",
            model_used="mock-model"
        )
    
    def validate_connection(self):
        return True
    
    def get_available_models(self):
        return ["mock-model-1", "mock-model-2"]


class TestTextGenerator(unittest.TestCase):
    """Test TextGenerator functionality."""
    
    def setUp(self):
        """Set up test generator with mock provider."""
        self.mock_provider = MockProvider()
        self.generator = TextGenerator(provider=self.mock_provider)
    
    def test_initialization(self):
        """Test TextGenerator initialization."""
        self.assertIsNotNone(self.generator.provider)
        self.assertIsNotNone(self.generator.config)
        self.assertEqual(len(self.generator.conversation_history), 0)
    
    def test_simple_generation(self):
        """Test basic text generation."""
        response = self.generator.generate("What is Python?", command_type="explain")
        self.assertIsInstance(response, str)
        self.assertEqual(response, "Mock response text")
    
    def test_generation_with_parameters(self):
        """Test text generation with custom parameters."""
        response = self.generator.generate(
            "Write a function", 
            command_type="code",
            model="custom-model",
            temperature=0.5,
            max_tokens=2048
        )
        self.assertIsInstance(response, str)
    
    def test_conversation_history(self):
        """Test conversation history management."""
        # Generate with history
        response1 = self.generator.generate_with_history("Hello")
        self.assertEqual(len(self.generator.conversation_history), 2)  # User + Assistant
        
        # Generate follow-up
        response2 = self.generator.generate_with_history("How are you?")
        self.assertEqual(len(self.generator.conversation_history), 4)  # 2 more messages
        
        # Clear history
        self.generator.clear_history()
        self.assertEqual(len(self.generator.conversation_history), 0)
    
    def test_conversation_export_import(self):
        """Test conversation export and import."""
        # Generate some conversation
        self.generator.generate_with_history("Hello")
        self.generator.generate_with_history("How are you?")
        
        # Export conversation
        exported = self.generator.export_conversation()
        self.assertIn('messages', exported)
        self.assertIn('provider', exported)
        self.assertEqual(len(exported['messages']), 4)
        
        # Clear and import
        self.generator.clear_history()
        self.generator.import_conversation(exported)
        self.assertEqual(len(self.generator.conversation_history), 4)
    
    def test_error_handling(self):
        """Test error handling."""
        # Test empty input
        with self.assertRaises(ValidationError):
            self.generator.generate("")
        
        # Test with provider that raises exception
        error_provider = Mock(spec=LLMProvider)
        error_provider.generate_text.side_effect = Exception("Provider error")
        
        error_generator = TextGenerator(provider=error_provider)
        with self.assertRaises(GenerationError):
            error_generator.generate("test")
    
    def test_available_models(self):
        """Test getting available models."""
        models = self.generator.get_available_models()
        self.assertIsInstance(models, list)
        self.assertIn("mock-model-1", models)


class TestImageGenerator(unittest.TestCase):
    """Test ImageGenerator functionality."""
    
    def setUp(self):
        """Set up test generator with mock provider."""
        self.mock_provider = MockProvider()
        self.generator = ImageGenerator(provider=self.mock_provider)
    
    def test_initialization(self):
        """Test ImageGenerator initialization."""
        self.assertIsNotNone(self.generator.provider)
        self.assertIsNotNone(self.generator.config)
    
    def test_image_generation(self):
        """Test basic image generation."""
        image_data = self.generator.generate("A mountain landscape")
        self.assertIsInstance(image_data, bytes)
        self.assertEqual(image_data, b"mock_image_data")
    
    def test_image_generation_with_parameters(self):
        """Test image generation with custom parameters."""
        image_data = self.generator.generate(
            "A sunset",
            size="1792x1024",
            quality="high"
        )
        self.assertIsInstance(image_data, bytes)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.abspath')
    def test_save_image(self, mock_abspath, mock_file):
        """Test image saving functionality."""
        mock_abspath.return_value = "/path/to/image.png"
        
        # Test saving image
        result_path = self.generator.save_image(b"test_data", "test_image")
        self.assertEqual(result_path, "/path/to/image.png")
        
        # Verify file was written
        mock_file.assert_called_once_with("/path/to/image.png", 'wb')
        mock_file().write.assert_called_once_with(b"test_data")
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.abspath')
    def test_generate_and_save(self, mock_abspath, mock_file):
        """Test generate and save in one operation."""
        mock_abspath.return_value = "/path/to/q_test_prompt.png"
        
        result_path = self.generator.generate_and_save("test prompt")
        self.assertEqual(result_path, "/path/to/q_test_prompt.png")
        
        # Verify file was written
        mock_file.assert_called_once()
        mock_file().write.assert_called_once_with(b"mock_image_data")
    
    def test_parameter_validation(self):
        """Test image parameter validation."""
        # Valid parameters
        self.assertTrue(self.generator.validate_image_params("1024x1024", "auto"))
        self.assertTrue(self.generator.validate_image_params("1792x1024", "high", "vivid"))
        
        # Invalid parameters
        self.assertFalse(self.generator.validate_image_params("invalid_size", "auto"))
        self.assertFalse(self.generator.validate_image_params("1024x1024", "invalid_quality"))
        self.assertFalse(self.generator.validate_image_params("1024x1024", "auto", "invalid_style"))
    
    def test_supported_sizes(self):
        """Test getting supported image sizes."""
        sizes = self.generator.get_supported_sizes()
        self.assertIsInstance(sizes, list)
        self.assertIn("1024x1024", sizes)
        self.assertIn("1792x1024", sizes)
    
    def test_cost_estimation(self):
        """Test cost estimation."""
        cost = self.generator.estimate_cost("1024x1024", "auto")
        self.assertIsInstance(cost, float)
        self.assertGreater(cost, 0)
    
    def test_error_handling(self):
        """Test error handling."""
        # Test empty prompt
        with self.assertRaises(ValidationError):
            self.generator.generate("")
        
        # Test invalid parameters
        with self.assertRaises(ValidationError):
            self.generator.generate("test", size="invalid")
        
        # Test empty image data
        with self.assertRaises(ValidationError):
            self.generator.save_image(b"", "test.png")
    
    def test_provider_without_image_support(self):
        """Test initialization with provider that doesn't support images."""
        non_image_provider = Mock(spec=LLMProvider)
        non_image_provider.supports_images = False
        
        with self.assertRaises(ValidationError):
            ImageGenerator(provider=non_image_provider)


if __name__ == '__main__':
    unittest.main()