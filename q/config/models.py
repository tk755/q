"""
Data models for configuration, requests, and responses.

These models provide type safety and structure for the Q library's
internal data handling while maintaining backward compatibility.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any, Union


class MessageRole(Enum):
    """Enumeration of message roles in conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    DEVELOPER = "developer"


@dataclass
class Message:
    """Represents a single message in a conversation."""
    role: MessageRole
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary format for API calls."""
        return {"role": self.role.value, "content": self.content}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Message":
        """Create message from dictionary format."""
        return cls(MessageRole(data["role"]), data["content"])


@dataclass
class ModelParameters:
    """Parameters for LLM model configuration."""
    model: str
    max_output_tokens: int = 1024
    temperature: float = 0.0
    tools: Optional[List[Dict[str, Any]]] = None
    
    def merge(self, other: "ModelParameters") -> "ModelParameters":
        """
        Merge with another ModelParameters, other takes precedence.
        
        Args:
            other: ModelParameters to merge with
            
        Returns:
            New ModelParameters with merged values
        """
        return ModelParameters(
            model=other.model if other.model else self.model,
            max_output_tokens=other.max_output_tokens if other.max_output_tokens != 1024 else self.max_output_tokens,
            temperature=other.temperature if other.temperature != 0.0 else self.temperature,
            tools=other.tools if other.tools is not None else self.tools
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class GenerationRequest:
    """Request object for text/image generation."""
    messages: List[Message]
    model_params: ModelParameters
    command_type: str = "default"


@dataclass
class GenerationResponse:
    """Response object from text/image generation."""
    text: Optional[str] = None
    image_data: Optional[bytes] = None
    model_used: Optional[str] = None
    usage_stats: Optional[Dict[str, Any]] = None
    raw_response: Optional[Any] = None


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    api_key: str
    base_url: Optional[str] = None
    timeout: int = 30
    model_mapping: Optional[Dict[str, str]] = None


@dataclass
class UserPreferences:
    """User preferences and default settings."""
    default_model: str = "gpt-4.1-mini"
    clip_output: bool = False
    verbose: bool = False
    save_conversations: bool = True
    auto_save_images: bool = True
    image_save_path: str = "."


@dataclass
class CommandDefaults:
    """Default settings for specific commands."""
    model_params: ModelParameters
    clip_output: bool = False