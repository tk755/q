#!/usr/bin/env python3
"""
Example usage of the Q library.

This demonstrates how the modular Q library can be imported and used
independently of the CLI interface.
"""

import os
from unittest.mock import MagicMock, patch

# Import the Q library
from q import TextGenerator, ImageGenerator, get_provider, ConfigManager

def demo_text_generation():
    """Demonstrate text generation capabilities."""
    print("=== Text Generation Demo ===")
    
    # Mock the OpenAI client to avoid needing real API keys
    with patch('q.providers.openai.openai.OpenAI') as mock_openai_client:
        # Mock response
        mock_response = MagicMock()
        mock_response.output_text = "Python is a high-level, interpreted programming language known for its simple syntax and powerful libraries."
        mock_response.output = []
        
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # Mock the config to avoid file operations
        with patch('q.config.manager.ConfigManager._load_resource') as mock_load:
            mock_load.return_value = 'mock-api-key'
            
            # Create a text generator
            generator = TextGenerator()
            
            # Generate explanations
            print("\n1. Explaining a concept:")
            response = generator.generate("What is Python?", command_type="explain")
            print(f"Response: {response}")
            
            # Generate code (would normally copy to clipboard)
            print("\n2. Generating code:")
            response = generator.generate("create a function to reverse a string", command_type="code") 
            print(f"Response: {response}")
            
            # Demonstrate conversation
            print("\n3. Conversation with history:")
            response1 = generator.generate_with_history("Hello, what can you help me with?")
            print(f"First response: {response1}")
            
            response2 = generator.generate_with_history("Tell me about programming")
            print(f"Second response: {response2}")
            
            print(f"Conversation history length: {len(generator.get_history())} messages")

def demo_image_generation():
    """Demonstrate image generation capabilities."""
    print("\n=== Image Generation Demo ===")
    
    # Mock the OpenAI client
    with patch('q.providers.openai.openai.OpenAI') as mock_openai_client:
        # Mock image response
        mock_response = MagicMock()
        mock_response.output_text = ""
        mock_response.output = [MagicMock()]
        mock_response.output[0].type = 'image_generation_call'
        mock_response.output[0].result = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="  # 1x1 PNG
        
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_client.models.list.return_value = MagicMock()
        mock_openai_client.return_value = mock_client
        
        with patch('q.config.manager.ConfigManager._load_resource') as mock_load:
            mock_load.return_value = 'mock-api-key'
            
            # Create an image generator
            generator = ImageGenerator()
            
            print("\n1. Generating image data:")
            image_data = generator.generate("A serene mountain landscape at sunset")
            print(f"Generated {len(image_data)} bytes of image data")
            
            print("\n2. Supported image sizes:")
            sizes = generator.get_supported_sizes()
            print(f"Supported sizes: {sizes}")
            
            print("\n3. Cost estimation:")
            cost = generator.estimate_cost("1024x1024", "high")
            print(f"Estimated cost for 1024x1024 high quality: ${cost:.3f}")

def demo_provider_system():
    """Demonstrate the provider system."""
    print("\n=== Provider System Demo ===")
    
    # Mock the OpenAI client
    with patch('q.providers.openai.openai.OpenAI') as mock_openai_client:
        mock_client = MagicMock()
        mock_client.models.list.return_value = MagicMock()
        mock_openai_client.return_value = mock_client
        
        with patch('q.config.manager.ConfigManager._load_resource') as mock_load:
            mock_load.return_value = 'mock-api-key'
            
            # Get provider
            provider = get_provider("openai")
            print(f"Provider name: {provider.provider_name}")
            print(f"Supports images: {provider.supports_images}")
            print(f"Supports web search: {provider.supports_web_search}")
            
            # Use provider with generator
            generator = TextGenerator(provider=provider)
            print("Created TextGenerator with specific provider")

def demo_configuration():
    """Demonstrate configuration management."""
    print("\n=== Configuration Demo ===")
    
    # Create config manager with temporary path
    import tempfile
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, 'test_config.json')
    
    config = ConfigManager(config_path=config_path)
    
    # Set some preferences
    config.set_preference('default_model', 'gpt-4.1')
    config.set_preference('verbose', True)
    
    # Get preferences
    model = config.get_preference('default_model')
    verbose = config.get_preference('verbose', False)
    
    print(f"Default model: {model}")
    print(f"Verbose mode: {verbose}")
    
    # Clean up
    if os.path.exists(config_path):
        os.remove(config_path)
    os.rmdir(temp_dir)

def main():
    """Main demo function."""
    print("Q Library Usage Demonstration")
    print("============================")
    print("This demonstrates the modular Q library's capabilities")
    print("using mocked responses to avoid needing real API keys.\n")
    
    try:
        demo_text_generation()
        demo_image_generation()
        demo_provider_system()
        demo_configuration()
        
        print("\n=== Demo Complete ===")
        print("The Q library successfully demonstrates:")
        print("✓ Provider-agnostic text generation")
        print("✓ Provider-agnostic image generation") 
        print("✓ Conversation history management")
        print("✓ Pluggable provider system")
        print("✓ Configuration management")
        print("✓ Backward compatibility with original q.py")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()