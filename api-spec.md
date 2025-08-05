# API Specification: Q Library

## Overview
This document defines the public API for the Q library, focusing on the provider-agnostic text and image generation classes that can be imported and used independently of the CLI interface.

## Core Library API

### TextGenerator Class

#### Constructor
```python
class TextGenerator:
    def __init__(
        self, 
        provider: Optional[LLMProvider] = None,
        config: Optional[ConfigManager] = None
    ) -> None:
        """
        Initialize TextGenerator with optional provider and configuration.
        
        Args:
            provider: LLM provider instance. If None, uses default OpenAI provider.
            config: Configuration manager. If None, creates default configuration.
        
        Raises:
            ConfigurationError: If API keys are not configured
            ProviderError: If provider initialization fails
        """
```

#### Text Generation Methods
```python
def generate(
    self, 
    text: str, 
    command_type: str = "default",
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Generate text response for given input.
    
    Args:
        text: Input text/prompt
        command_type: Type of command (default, explain, code, shell, web)
        model: Override default model
        temperature: Override default temperature (0.0-2.0)
        max_tokens: Override default max tokens
    
    Returns:
        Generated text response, processed and formatted
        
    Raises:
        GenerationError: If generation fails
        ValidationError: If input parameters are invalid
    """

def generate_with_history(
    self,
    text: str,
    command_type: str = "default",
    **kwargs
) -> str:
    """
    Generate text response maintaining conversation history.
    
    Args:
        text: Input text/prompt
        command_type: Type of command
        **kwargs: Same options as generate()
    
    Returns:
        Generated text response with conversation context
        
    Raises:
        GenerationError: If generation fails
    """

def generate_raw(
    self,
    messages: List[Message],
    model_params: ModelParameters
) -> GenerationResponse:
    """
    Low-level generation method for advanced users.
    
    Args:
        messages: List of conversation messages
        model_params: Model parameters object
    
    Returns:
        Raw generation response object
        
    Raises:
        GenerationError: If generation fails
    """
```

#### Conversation Management
```python
def clear_history(self) -> None:
    """Clear conversation history."""

def get_history(self) -> List[Message]:
    """Get current conversation history."""

def set_history(self, messages: List[Message]) -> None:
    """Set conversation history."""

def export_conversation(self) -> Dict[str, Any]:
    """Export conversation as JSON-serializable dict."""

def import_conversation(self, data: Dict[str, Any]) -> None:
    """Import conversation from exported data."""
```

#### Configuration Methods
```python
def set_default_model(self, model: str) -> None:
    """Set default model for this generator instance."""

def set_provider(self, provider: LLMProvider) -> None:
    """Change the LLM provider."""

def get_available_models(self) -> List[str]:
    """Get list of available models from current provider."""
```

### ImageGenerator Class

#### Constructor
```python
class ImageGenerator:
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        config: Optional[ConfigManager] = None
    ) -> None:
        """
        Initialize ImageGenerator with optional provider and configuration.
        
        Args:
            provider: LLM provider instance supporting image generation
            config: Configuration manager
            
        Raises:
            ConfigurationError: If API keys are not configured
            ProviderError: If provider doesn't support image generation
        """
```

#### Image Generation Methods
```python
def generate(
    self,
    prompt: str,
    size: str = "1024x1024",
    quality: str = "auto",
    style: Optional[str] = None
) -> bytes:
    """
    Generate image from text prompt.
    
    Args:
        prompt: Text description of desired image
        size: Image dimensions (256x256, 512x512, 1024x1024, 1792x1024, 1024x1792)
        quality: Image quality (auto, low, medium, high)
        style: Image style (vivid, natural)
    
    Returns:
        Image data as bytes (PNG format)
        
    Raises:
        GenerationError: If image generation fails
        ValidationError: If parameters are invalid
    """

def generate_and_save(
    self,
    prompt: str,
    filename: Optional[str] = None,
    **kwargs
) -> str:
    """
    Generate image and save to file.
    
    Args:
        prompt: Text description of desired image
        filename: Output filename. If None, auto-generates based on prompt
        **kwargs: Same options as generate()
    
    Returns:
        Path to saved image file
        
    Raises:
        GenerationError: If generation fails
        IOError: If file cannot be saved
    """

def save_image(self, image_data: bytes, filename: str) -> str:
    """
    Save image data to file.
    
    Args:
        image_data: Raw image bytes
        filename: Output filename
    
    Returns:
        Full path to saved file
        
    Raises:
        IOError: If file cannot be saved
        ValidationError: If image data is invalid
    """
```

#### Utility Methods
```python
def validate_image_params(
    self,
    size: str,
    quality: str,
    style: Optional[str] = None
) -> bool:
    """Validate image generation parameters."""

def get_supported_sizes(self) -> List[str]:
    """Get list of supported image sizes."""

def estimate_cost(self, size: str, quality: str) -> float:
    """Estimate generation cost in USD."""
```

## Provider Interface

### LLMProvider Abstract Base Class
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_text(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text response from request."""
        pass
    
    @abstractmethod
    def generate_image(self, request: GenerationRequest) -> GenerationResponse:
        """Generate image response from request."""
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Test if provider connection is working."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass
    
    @property
    @abstractmethod
    def supports_images(self) -> bool:
        """Whether provider supports image generation."""
        pass
    
    @property
    @abstractmethod
    def supports_web_search(self) -> bool:
        """Whether provider supports web search."""
        pass
```

### Provider Factory
```python
def get_provider(
    provider_name: str = "openai",
    config: Optional[ConfigManager] = None,
    **kwargs
) -> LLMProvider:
    """
    Get provider instance by name.
    
    Args:
        provider_name: Name of provider (openai, anthropic, etc.)
        config: Configuration manager
        **kwargs: Provider-specific configuration
    
    Returns:
        Configured provider instance
        
    Raises:
        ProviderNotFoundError: If provider is not available
        ConfigurationError: If provider configuration is invalid
    """

def register_provider(name: str, provider_class: type) -> None:
    """Register a new provider class."""

def list_providers() -> List[str]:
    """List all available provider names."""
```

## Command Interface

### BaseCommand Abstract Class
```python
class BaseCommand(ABC):
    """Abstract base class for commands."""
    
    @abstractmethod
    def get_messages(self, text: str) -> List[Message]:
        """Get message list for this command."""
        pass
    
    @abstractmethod
    def get_model_params(self) -> ModelParameters:
        """Get model parameters for this command."""
        pass
    
    @property
    @abstractmethod
    def flags(self) -> List[str]:
        """Command flags (e.g., ['-c', '--code'])."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description for help text."""
        pass
    
    @property
    def clip_output(self) -> bool:
        """Whether to copy output to clipboard by default."""
        return False
    
    def validate_input(self, text: str) -> bool:
        """Validate command input."""
        return len(text.strip()) > 0
    
    def process_response(self, response: str) -> str:
        """Post-process command response."""
        return response
```

### Command Registration
```python
def register_command(command_class: type) -> None:
    """Register a new command class."""

def get_command(flag: str) -> Optional[BaseCommand]:
    """Get command instance by flag."""

def list_commands() -> List[BaseCommand]:
    """List all registered commands."""
```

## Configuration Management API

### ConfigManager Class
```python
class ConfigManager:
    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. Uses default if None.
        """
    
    # API Key Management
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider."""
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """Set API key for provider."""
    
    def validate_api_key(self, provider: str) -> bool:
        """Validate API key for provider."""
    
    # User Preferences
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference value."""
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set user preference value."""
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
    
    # Model Configuration
    def get_model_defaults(self, command_type: str) -> ModelParameters:
        """Get default model parameters for command type."""
    
    def set_model_defaults(self, command_type: str, params: ModelParameters) -> None:
        """Set default model parameters for command type."""
    
    # Conversation History
    def save_conversation(self, messages: List[Message]) -> None:
        """Save conversation history."""
    
    def load_conversation(self) -> List[Message]:
        """Load conversation history."""
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
    
    # Configuration Persistence
    def save(self) -> None:
        """Save configuration to file."""
    
    def reload(self) -> None:
        """Reload configuration from file."""
    
    def migrate_from_old_format(self) -> bool:
        """Migrate from old resources.json format."""
```

## Data Models

### Core Models
```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any, Union

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    DEVELOPER = "developer"

@dataclass
class Message:
    role: MessageRole
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Message":
        return cls(MessageRole(data["role"]), data["content"])

@dataclass
class ModelParameters:
    model: str
    max_output_tokens: int = 1024
    temperature: float = 0.0
    tools: Optional[List[Dict[str, Any]]] = None
    
    def merge(self, other: "ModelParameters") -> "ModelParameters":
        """Merge with another ModelParameters, other takes precedence."""
        return ModelParameters(
            model=other.model if other.model else self.model,
            max_output_tokens=other.max_output_tokens if other.max_output_tokens != 1024 else self.max_output_tokens,
            temperature=other.temperature if other.temperature != 0.0 else self.temperature,
            tools=other.tools if other.tools is not None else self.tools
        )

@dataclass
class GenerationRequest:
    messages: List[Message]
    model_params: ModelParameters
    command_type: str = "default"

@dataclass
class GenerationResponse:
    text: Optional[str] = None
    image_data: Optional[bytes] = None
    model_used: Optional[str] = None
    usage_stats: Optional[Dict[str, Any]] = None
    raw_response: Optional[Any] = None
```

### Configuration Models
```python
@dataclass
class ProviderConfig:
    api_key: str
    base_url: Optional[str] = None
    timeout: int = 30
    model_mapping: Optional[Dict[str, str]] = None

@dataclass
class UserPreferences:
    default_model: str = "gpt-4.1-mini"
    clip_output: bool = False
    verbose: bool = False
    save_conversations: bool = True
    auto_save_images: bool = True
    image_save_path: str = "."

@dataclass
class CommandDefaults:
    model_params: ModelParameters
    clip_output: bool = False
```

## Error Handling

### Exception Hierarchy
```python
class QError(Exception):
    """Base exception for Q library."""
    pass

class ConfigurationError(QError):
    """Configuration-related errors."""
    pass

class ProviderError(QError):
    """Provider-related errors."""
    pass

class ProviderNotFoundError(ProviderError):
    """Provider not found or not available."""
    pass

class GenerationError(QError):
    """Text/image generation errors."""
    pass

class ValidationError(QError):
    """Input validation errors."""
    pass

class AuthenticationError(ProviderError):
    """API authentication errors."""
    pass

class RateLimitError(ProviderError):
    """API rate limit exceeded."""
    pass

class InsufficientCreditsError(ProviderError):
    """Insufficient API credits."""
    pass
```

### Error Context
```python
@dataclass
class ErrorContext:
    operation: str
    provider: Optional[str] = None
    model: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    
class QError(Exception):
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context
```

## Usage Examples

### Basic Text Generation
```python
from q import TextGenerator

# Simple usage with defaults
generator = TextGenerator()
response = generator.generate("Explain how to use git rebase", command_type="explain")
print(response)

# With custom model
response = generator.generate(
    "Write a Python function to sort a list", 
    command_type="code",
    model="gpt-4.1",
    temperature=0.1
)
print(response)
```

### Conversation with History
```python
from q import TextGenerator

generator = TextGenerator()

# First question
response1 = generator.generate_with_history("What is Python?")
print("Q:", "What is Python?")
print("A:", response1)

# Follow-up question
response2 = generator.generate_with_history("What are its main features?")
print("Q:", "What are its main features?")
print("A:", response2)

# Export conversation
conversation_data = generator.export_conversation()
```

### Image Generation
```python
from q import ImageGenerator

generator = ImageGenerator()

# Generate and save image
image_path = generator.generate_and_save(
    "A serene mountain landscape at sunset",
    size="1792x1024",
    quality="high"
)
print(f"Image saved to: {image_path}")

# Generate raw image data
image_data = generator.generate(
    "A robot writing code",
    size="1024x1024"
)
# Process image_data as needed
```

### Custom Provider
```python
from q import TextGenerator, get_provider
from q.providers.base import LLMProvider

# Use specific provider
openai_provider = get_provider("openai")
generator = TextGenerator(provider=openai_provider)

# Custom provider implementation
class CustomProvider(LLMProvider):
    def generate_text(self, request):
        # Implementation
        pass
    
    def generate_image(self, request):
        # Implementation
        pass
    
    # ... other required methods

# Register and use custom provider
from q.providers import register_provider
register_provider("custom", CustomProvider)
custom_provider = get_provider("custom")
generator = TextGenerator(provider=custom_provider)
```

### Configuration Management
```python
from q import ConfigManager, TextGenerator

# Custom configuration
config = ConfigManager()
config.set_api_key("openai", "your-api-key")
config.set_preference("default_model", "gpt-4.1")

# Use with generator
generator = TextGenerator(config=config)
```

### Advanced Usage
```python
from q import TextGenerator
from q.config.models import Message, MessageRole, ModelParameters

generator = TextGenerator()

# Low-level API usage
messages = [
    Message(MessageRole.DEVELOPER, "You are a helpful coding assistant."),
    Message(MessageRole.USER, "Write a Python function to calculate fibonacci numbers.")
]

model_params = ModelParameters(
    model="gpt-4.1",
    temperature=0.2,
    max_output_tokens=2048
)

response = generator.generate_raw(messages, model_params)
print(response.text)
print(f"Model used: {response.model_used}")
print(f"Usage: {response.usage_stats}")
```

## Async Support (Future)

### Async Generators
```python
# Future async API design
class AsyncTextGenerator:
    async def generate(self, text: str, **kwargs) -> str:
        """Async text generation."""
        pass
    
    async def generate_stream(self, text: str, **kwargs) -> AsyncIterator[str]:
        """Streaming text generation."""
        async for chunk in self._generate_chunks(text, **kwargs):
            yield chunk

# Usage
async def example():
    generator = AsyncTextGenerator()
    
    # Async generation
    response = await generator.generate("Explain async programming")
    
    # Streaming generation
    async for chunk in generator.generate_stream("Write a story"):
        print(chunk, end="", flush=True)
```

## Versioning and Compatibility

### API Versioning
- **Semantic Versioning**: Major.Minor.Patch
- **Breaking Changes**: Only in major versions
- **Deprecation Policy**: 2 minor versions before removal
- **Backward Compatibility**: Maintained within major versions

### Version Information
```python
import q
print(q.__version__)  # "2.0.0"
print(q.__api_version__)  # "1.0"

# Check compatibility
from q.utils import check_compatibility
is_compatible = check_compatibility("1.0")
```

This API specification provides a comprehensive interface for the Q library, enabling both simple usage and advanced customization while maintaining clean separation between CLI and library functionality.