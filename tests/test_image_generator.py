"""
Comprehensive unit tests for ImageGenerator class.

Tests the provider-agnostic image generation functionality including:
- Basic image generation
- Image saving and file operations
- Parameter validation
- Error handling
- Cost estimation
- Provider integration
"""

import pytest
import os
import base64
from unittest.mock import Mock, patch, mock_open, MagicMock

from q.generators.image import ImageGenerator
from q.config.models import ModelParameters, GenerationRequest, GenerationResponse
from q.utils.exceptions import GenerationError, ValidationError
from tests.conftest import MockProvider, create_test_image_data, assert_valid_image_data


@pytest.mark.unit
class TestImageGenerator:
    """Test ImageGenerator functionality."""
    
    def test_initialization_with_defaults(self):
        """Test ImageGenerator initialization with default parameters."""
        with patch('q.generators.image.get_default_provider') as mock_get_provider, \
             patch('q.generators.image.ConfigManager') as mock_config:
            
            mock_provider = MockProvider(supports_images=True)
            mock_get_provider.return_value = mock_provider
            mock_config.return_value = Mock()
            
            generator = ImageGenerator()
            
            assert generator.provider == mock_provider
            assert generator.config is not None
    
    def test_initialization_with_custom_provider(self, mock_provider):
        """Test ImageGenerator initialization with custom provider."""
        generator = ImageGenerator(provider=mock_provider)
        
        assert generator.provider == mock_provider
    
    def test_initialization_with_non_image_provider(self, mock_provider_no_images):
        """Test initialization fails with provider that doesn't support images."""
        with pytest.raises(ValidationError, match="does not support image generation"):
            ImageGenerator(provider=mock_provider_no_images)
    
    def test_basic_image_generation(self, mock_provider):
        """Test basic image generation."""
        generator = ImageGenerator(provider=mock_provider)
        
        image_data = generator.generate("A beautiful sunset")
        
        assert_valid_image_data(image_data)
        assert image_data == b"mock_image_data_12345"
    
    def test_image_generation_with_parameters(self, mock_provider):
        """Test image generation with custom parameters."""
        generator = ImageGenerator(provider=mock_provider)
        
        image_data = generator.generate(
            "A mountain landscape",
            size="1792x1024",
            quality="high",
            style="vivid"
        )
        
        assert_valid_image_data(image_data)
    
    def test_generate_and_save(self, mock_provider):
        """Test generate and save in one operation."""
        generator = ImageGenerator(provider=mock_provider)
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.abspath', return_value="/test/path/image.png"):
            
            result_path = generator.generate_and_save("A test image")
            
            assert result_path == "/test/path/image.png"
            mock_file.assert_called_once_with("/test/path/image.png", 'wb')
            mock_file().write.assert_called_once_with(b"mock_image_data_12345")
    
    def test_generate_and_save_with_custom_filename(self, mock_provider):
        """Test generate and save with custom filename."""
        generator = ImageGenerator(provider=mock_provider)
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.abspath', return_value="/test/path/custom.png"):
            
            result_path = generator.generate_and_save("A test image", filename="custom")
            
            assert result_path == "/test/path/custom.png"
            mock_file.assert_called_once_with("/test/path/custom.png", 'wb')
    
    def test_save_image(self, mock_provider):
        """Test image saving functionality."""
        generator = ImageGenerator(provider=mock_provider)
        test_data = create_test_image_data()
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.abspath', return_value="/test/path/test.png"):
            
            result_path = generator.save_image(test_data, "test.png")
            
            assert result_path == "/test/path/test.png"
            mock_file.assert_called_once_with("/test/path/test.png", 'wb')
            mock_file().write.assert_called_once_with(test_data)
    
    def test_save_image_adds_png_extension(self, mock_provider):
        """Test that PNG extension is added if missing."""
        generator = ImageGenerator(provider=mock_provider)
        test_data = create_test_image_data()
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.abspath', return_value="/test/path/test.png"):
            
            result_path = generator.save_image(test_data, "test")  # No extension
            
            assert result_path == "/test/path/test.png"
            mock_file.assert_called_once_with("/test/path/test.png", 'wb')
    
    def test_filename_generation(self, mock_provider):
        """Test filename generation from prompt."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Test various prompts
        test_cases = [
            ("A beautiful sunset", "q_A_beautiful_sunset.png"),
            ("Mountain landscape!", "q_Mountain_landscape.png"),
            ("Test with @#$% special chars", "q_Test_with__special_chars.png"),
            ("Multiple   spaces", "q_Multiple___spaces.png")
        ]
        
        for prompt, expected in test_cases:
            filename = generator._generate_filename(prompt)
            assert filename == expected
    
    def test_parameter_validation(self, mock_provider):
        """Test image parameter validation."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Valid parameters
        assert generator.validate_image_params("1024x1024", "auto") == True
        assert generator.validate_image_params("1792x1024", "high", "vivid") == True
        assert generator.validate_image_params("512x512", "low", "natural") == True
        
        # Invalid size
        assert generator.validate_image_params("invalid_size", "auto") == False
        assert generator.validate_image_params("2048x2048", "auto") == False
        
        # Invalid quality
        assert generator.validate_image_params("1024x1024", "invalid_quality") == False
        assert generator.validate_image_params("1024x1024", "ultra") == False
        
        # Invalid style
        assert generator.validate_image_params("1024x1024", "auto", "invalid_style") == False
        assert generator.validate_image_params("1024x1024", "auto", "cartoon") == False
    
    def test_supported_sizes(self, mock_provider):
        """Test getting supported image sizes."""
        generator = ImageGenerator(provider=mock_provider)
        
        sizes = generator.get_supported_sizes()
        
        assert isinstance(sizes, list)
        expected_sizes = ['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792']
        assert sizes == expected_sizes
    
    def test_cost_estimation(self, mock_provider):
        """Test cost estimation functionality."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Test different size and quality combinations
        test_cases = [
            ("1024x1024", "auto", 0.020),
            ("1792x1024", "high", 0.048),  # 0.040 * 1.2
            ("512x512", "low", 0.0144),    # 0.018 * 0.8
        ]
        
        for size, quality, expected_cost in test_cases:
            cost = generator.estimate_cost(size, quality)
            assert isinstance(cost, float)
            assert cost == pytest.approx(expected_cost, rel=1e-3)
    
    def test_cost_estimation_with_unknown_params(self, mock_provider):
        """Test cost estimation with unknown parameters."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Unknown size should use default
        cost = generator.estimate_cost("unknown_size", "auto")
        assert cost == 0.020  # Default cost
        
        # Unknown quality should use default multiplier
        cost = generator.estimate_cost("1024x1024", "unknown_quality")
        assert cost == 0.020  # 0.020 * 1.0 (default multiplier)
    
    # Error handling tests
    def test_empty_prompt_validation(self, mock_provider):
        """Test validation of empty prompt."""
        generator = ImageGenerator(provider=mock_provider)
        
        with pytest.raises(ValidationError, match="Image prompt cannot be empty"):
            generator.generate("")
        
        with pytest.raises(ValidationError, match="Image prompt cannot be empty"):
            generator.generate("   ")  # Only whitespace
    
    def test_invalid_parameters_validation(self, mock_provider):
        """Test validation of invalid parameters."""
        generator = ImageGenerator(provider=mock_provider)
        
        with pytest.raises(ValidationError, match="Invalid image parameters"):
            generator.generate("test", size="invalid_size")
        
        with pytest.raises(ValidationError, match="Invalid image parameters"):
            generator.generate("test", quality="invalid_quality")
        
        with pytest.raises(ValidationError, match="Invalid image parameters"):
            generator.generate("test", style="invalid_style")
    
    def test_provider_error_handling(self, mock_provider):
        """Test handling of provider errors."""
        mock_provider.set_failure_mode(True)
        generator = ImageGenerator(provider=mock_provider)
        
        with pytest.raises(GenerationError, match="Image generation failed"):
            generator.generate("Test image")
    
    def test_empty_image_data_handling(self, mock_provider):
        """Test handling of empty image data from provider."""
        # Mock provider to return empty image data
        mock_response = GenerationResponse(
            text="Generated image",
            image_data=None,  # Empty image data
            model_used="test"
        )
        mock_provider.generate_image = Mock(return_value=mock_response)
        
        generator = ImageGenerator(provider=mock_provider)
        
        with pytest.raises(GenerationError, match="No image data received from provider"):
            generator.generate("Test image")
    
    def test_save_empty_image_data(self, mock_provider):
        """Test saving empty image data raises error."""
        generator = ImageGenerator(provider=mock_provider)
        
        with pytest.raises(ValidationError, match="Image data cannot be empty"):
            generator.save_image(b"", "test.png")
    
    def test_save_empty_filename(self, mock_provider):
        """Test saving with empty filename raises error."""
        generator = ImageGenerator(provider=mock_provider)
        test_data = create_test_image_data()
        
        with pytest.raises(ValidationError, match="Filename cannot be empty"):
            generator.save_image(test_data, "")
    
    def test_file_save_error_handling(self, mock_provider):
        """Test handling of file save errors."""
        generator = ImageGenerator(provider=mock_provider)
        test_data = create_test_image_data()
        
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError, match="Failed to save image"):
                generator.save_image(test_data, "test.png")
    
    def test_image_generation_request_format(self, mock_provider):
        """Test that image generation creates proper request format."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Mock the provider to capture the request
        captured_requests = []
        original_generate = mock_provider.generate_image
        
        def capture_request(request):
            captured_requests.append(request)
            return original_generate(request)
        
        mock_provider.generate_image = capture_request
        
        # Generate image
        generator.generate("A test image", size="1792x1024", quality="high", style="vivid")
        
        # Check request format
        assert len(captured_requests) == 1
        request = captured_requests[0]
        
        assert isinstance(request, GenerationRequest)
        assert len(request.messages) == 1
        assert "A test image" in request.messages[0].content
        assert request.command_type == "image"
        
        # Check model parameters
        assert request.model_params.model == 'gpt-4.1-mini'
        assert request.model_params.temperature == 0.0
        assert request.model_params.tools is not None
        assert len(request.model_params.tools) == 1
        
        # Check tool parameters
        tool = request.model_params.tools[0]
        assert tool['type'] == 'image_generation'
        assert tool['size'] == '1792x1024'
        assert tool['quality'] == 'high'
        assert tool['style'] == 'vivid'
    
    def test_image_generation_without_style(self, mock_provider):
        """Test image generation without style parameter."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Mock the provider to capture the request
        captured_requests = []
        original_generate = mock_provider.generate_image
        
        def capture_request(request):
            captured_requests.append(request)
            return original_generate(request)
        
        mock_provider.generate_image = capture_request
        
        # Generate image without style
        generator.generate("A test image", size="1024x1024", quality="auto")
        
        # Check that style is not included in tools
        request = captured_requests[0]
        tool = request.model_params.tools[0]
        assert 'style' not in tool
    
    @pytest.mark.performance
    def test_image_generation_performance(self, mock_provider):
        """Test that image generation completes within reasonable time."""
        import time
        
        generator = ImageGenerator(provider=mock_provider)
        
        start_time = time.time()
        generator.generate("Test performance")
        end_time = time.time()
        
        # Should complete within 2 seconds for mock provider
        assert (end_time - start_time) < 2.0
    
    def test_concurrent_image_generation(self, mock_provider):
        """Test concurrent image generation."""
        import threading
        
        generator = ImageGenerator(provider=mock_provider)
        results = []
        errors = []
        
        def generate_image(prompt):
            try:
                result = generator.generate(f"Image {prompt}")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple generations concurrently
        threads = []
        for i in range(3):  # Fewer threads for image generation
            thread = threading.Thread(target=generate_image, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3
        for result in results:
            assert_valid_image_data(result)


@pytest.mark.integration
class TestImageGeneratorIntegration:
    """Integration tests for ImageGenerator with real-like scenarios."""
    
    def test_with_mock_openai_provider(self, mock_openai_image_client):
        """Test ImageGenerator with mocked OpenAI provider."""
        with patch('q.providers.openai.openai.OpenAI', return_value=mock_openai_image_client), \
             patch('q.config.manager.ConfigManager._load_resource', return_value='test-key'):
            
            from q.providers.openai import OpenAIProvider
            provider = OpenAIProvider()
            generator = ImageGenerator(provider=provider)
            
            image_data = generator.generate("A beautiful landscape")
            
            assert_valid_image_data(image_data)
    
    def test_full_workflow_generate_and_save(self, mock_provider, tmp_path):
        """Test complete workflow from generation to file save."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Generate and save to temporary directory
        test_filename = tmp_path / "test_image.png"
        
        with patch('os.path.abspath', return_value=str(test_filename)):
            with patch('builtins.open', mock_open()) as mock_file:
                result_path = generator.generate_and_save(
                    "A test landscape",
                    filename=str(test_filename)
                )
                
                assert result_path == str(test_filename)
                mock_file.assert_called_once_with(str(test_filename), 'wb')
    
    def test_filename_compatibility_with_original_q(self, mock_provider):
        """Test that filename generation matches original q.py behavior."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Test cases that should match original q.py behavior
        test_cases = [
            "mountain landscape",
            "a serene lake at sunset!",
            "futuristic city with flying cars?",
            "abstract art: geometric shapes & colors"
        ]
        
        for prompt in test_cases:
            filename = generator._generate_filename(prompt)
            
            # Should start with 'q_'
            assert filename.startswith('q_')
            
            # Should end with '.png'
            assert filename.endswith('.png')
            
            # Should not contain punctuation
            import string
            content = filename[2:-4]  # Remove 'q_' and '.png'
            for char in content:
                assert char not in string.punctuation or char == '_'
    
    def test_parameter_validation_edge_cases(self, mock_provider):
        """Test parameter validation with edge cases."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Test case sensitivity
        assert generator.validate_image_params("1024x1024", "AUTO") == False  # Should be lowercase
        assert generator.validate_image_params("1024X1024", "auto") == False  # Should be lowercase x
        
        # Test with None values
        assert generator.validate_image_params("1024x1024", "auto", None) == True
        
        # Test with empty strings
        assert generator.validate_image_params("", "auto", None) == False
        assert generator.validate_image_params("1024x1024", "", None) == False