"""
Provider-agnostic text generation class.

Provides a clean, library-friendly interface for text generation that can be
used independently of the CLI while maintaining compatibility with all features.
"""

from typing import Optional, List, Dict, Any
from ..providers.base import LLMProvider
from ..providers.factory import get_default_provider
from ..config.manager import ConfigManager
from ..config.models import Message, MessageRole, ModelParameters, GenerationRequest, GenerationResponse
from ..commands.registry import get_command, get_default_command
from ..utils.processing import ResponseProcessor
from ..utils.exceptions import GenerationError, ValidationError


class TextGenerator:
    """
    Provider-agnostic text generation class.
    
    This class provides a clean interface for text generation that can be imported
    and used by other programs without any CLI dependencies. It supports both
    simple generation and conversation history management.
    
    Example:
        generator = TextGenerator()
        response = generator.generate("Explain Python decorators", command_type="explain")
        print(response)
    """
    
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
        self.provider = provider or get_default_provider()
        self.config = config or ConfigManager()
        self.conversation_history: List[Message] = []
        self.processor = ResponseProcessor()
    
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
        if not text.strip():
            raise ValidationError("Input text cannot be empty")
        
        # Get command configuration
        command = get_command(f"-{command_type[0]}") if command_type != "default" else get_default_command()
        if not command:
            command = get_default_command()
        
        if not command:
            raise ValidationError(f"Unknown command type: {command_type}")
        
        # Get messages and model parameters from command
        messages = command.get_messages(text)
        model_params = command.get_model_params()
        
        # Override parameters if provided
        if model:
            model_params.model = model
        if temperature is not None:
            model_params.temperature = temperature
        if max_tokens:
            model_params.max_output_tokens = max_tokens
        
        # Create generation request
        request = GenerationRequest(
            messages=messages,
            model_params=model_params,
            command_type=command_type
        )
        
        try:
            # Generate response
            response = self.provider.generate_text(request)
            
            if not response.text:
                raise GenerationError("No text response received from provider")
            
            # Process response
            processed_text = self.processor.process_text_response(response.text)
            processed_text = command.process_response(processed_text)
            
            return processed_text
            
        except (GenerationError, ValidationError):
            raise
        except Exception as e:
            raise GenerationError(f"Text generation failed: {e}")
    
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
        if not text.strip():
            raise ValidationError("Input text cannot be empty")
        
        try:
            # Add user message to history
            user_message = Message(role=MessageRole.USER, content=text)
            self.conversation_history.append(user_message)
            
            # For default command, use conversation history
            if command_type == "default":
                # Create custom request with full history
                model_params = self.config.get_model_defaults()
                
                # Override parameters if provided
                if 'model' in kwargs:
                    model_params.model = kwargs['model']
                if 'temperature' in kwargs:
                    model_params.temperature = kwargs['temperature']
                if 'max_tokens' in kwargs:
                    model_params.max_output_tokens = kwargs['max_tokens']
                
                request = GenerationRequest(
                    messages=self.conversation_history.copy(),
                    model_params=model_params,
                    command_type=command_type
                )
                
                response = self.provider.generate_text(request)
                
                if not response.text:
                    raise GenerationError("No text response received from provider")
                
                processed_text = self.processor.process_text_response(response.text)
                
                # Add assistant response to history
                assistant_message = Message(role=MessageRole.ASSISTANT, content=processed_text)
                self.conversation_history.append(assistant_message)
                
                return processed_text
            else:
                # For other commands, use regular generation
                response = self.generate(text, command_type, **kwargs)
                
                # Add to history for context
                assistant_message = Message(role=MessageRole.ASSISTANT, content=response)
                self.conversation_history.append(assistant_message)
                
                return response
                
        except (GenerationError, ValidationError):
            raise
        except Exception as e:
            raise GenerationError(f"Text generation with history failed: {e}")
    
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
        if not messages:
            raise ValidationError("Messages list cannot be empty")
        
        request = GenerationRequest(
            messages=messages,
            model_params=model_params,
            command_type="raw"
        )
        
        try:
            return self.provider.generate_text(request)
        except Exception as e:
            raise GenerationError(f"Raw text generation failed: {e}")
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
    
    def get_history(self) -> List[Message]:
        """Get current conversation history."""
        return self.conversation_history.copy()
    
    def set_history(self, messages: List[Message]) -> None:
        """Set conversation history."""
        self.conversation_history = messages.copy()
    
    def export_conversation(self) -> Dict[str, Any]:
        """
        Export conversation as JSON-serializable dict.
        
        Returns:
            Dictionary containing conversation data
        """
        return {
            'messages': [msg.to_dict() for msg in self.conversation_history],
            'provider': self.provider.provider_name,
            'version': '2.0'
        }
    
    def import_conversation(self, data: Dict[str, Any]) -> None:
        """
        Import conversation from exported data.
        
        Args:
            data: Dictionary containing conversation data
        """
        if 'messages' in data:
            messages = []
            for msg_data in data['messages']:
                try:
                    messages.append(Message.from_dict(msg_data))
                except (ValueError, KeyError):
                    # Skip invalid messages
                    continue
            self.conversation_history = messages
    
    def set_default_model(self, model: str) -> None:
        """Set default model for this generator instance."""
        # This would update the local config or provider settings
        pass
    
    def set_provider(self, provider: LLMProvider) -> None:
        """Change the LLM provider."""
        self.provider = provider
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from current provider."""
        return self.provider.get_available_models()