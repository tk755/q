"""
Configuration management with backward compatibility.

Maintains compatibility with the existing ~/.q/resources.json format
while providing structured configuration management for the modular system.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from .models import Message, MessageRole, ModelParameters, UserPreferences, ProviderConfig
from ..utils.exceptions import ConfigurationError


class ConfigManager:
    """
    Manages configuration with backward compatibility for existing ~/.q/resources.json format.
    
    This class provides the same interface as the original _load_resource and _save_resource
    functions while adding structured configuration management capabilities.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. Uses default ~/.q/resources.json if None.
        """
        self.config_path = config_path or self._default_config_path()
        self._ensure_config_dir()
        self._config_cache: Dict[str, Any] = {}
        self._load_config()
    
    def _default_config_path(self) -> str:
        """Get the default configuration path (~/.q/resources.json)."""
        return os.path.join(os.path.expanduser('~'), '.q', 'resources.json')
    
    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        config_dir = os.path.dirname(self.config_path)
        os.makedirs(config_dir, exist_ok=True)
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self._config_cache = json.load(f)
            else:
                self._config_cache = {}
        except (json.JSONDecodeError, IOError) as e:
            raise ConfigurationError(f"Failed to load configuration from {self.config_path}: {e}")
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config_cache, f, indent=4)
        except IOError as e:
            raise ConfigurationError(f"Failed to save configuration to {self.config_path}: {e}")
    
    # Backward compatibility methods - exact same interface as original q.py
    def _load_resource(self, name: str, default: Any) -> Any:
        """
        Load resource with backward compatibility.
        
        Maintains exact same interface as original _load_resource function.
        
        Args:
            name: Resource name
            default: Default value if resource doesn't exist
            
        Returns:
            Resource value or default
        """
        return self._config_cache.get(name, default)
    
    def _save_resource(self, name: str, value: Any) -> None:
        """
        Save resource with backward compatibility.
        
        Maintains exact same interface as original _save_resource function.
        
        Args:
            name: Resource name
            value: Resource value
        """
        self._config_cache[name] = value
        self._save_config()
    
    # New structured API methods
    def get_api_key(self, provider: str = "openai") -> Optional[str]:
        """
        Get API key for provider.
        
        Args:
            provider: Provider name (default: openai)
            
        Returns:
            API key or None if not found
        """
        # Check new format first
        providers = self._config_cache.get('providers', {})
        if provider in providers:
            return providers[provider].get('api_key')
        
        # Fallback to old format for backward compatibility
        if provider == "openai":
            return self._config_cache.get('openai_key')
        
        return None
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        Set API key for provider.
        
        Args:
            provider: Provider name
            api_key: API key value
        """
        # Save in new structured format
        if 'providers' not in self._config_cache:
            self._config_cache['providers'] = {}
        
        if provider not in self._config_cache['providers']:
            self._config_cache['providers'][provider] = {}
        
        self._config_cache['providers'][provider]['api_key'] = api_key
        
        # Maintain backward compatibility for OpenAI
        if provider == "openai":
            self._config_cache['openai_key'] = api_key
        
        self._save_config()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get user preference value.
        
        Args:
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value or default
        """
        preferences = self._config_cache.get('preferences', {})
        return preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set user preference value.
        
        Args:
            key: Preference key
            value: Preference value
        """
        if 'preferences' not in self._config_cache:
            self._config_cache['preferences'] = {}
        
        self._config_cache['preferences'][key] = value
        self._save_config()
    
    def get_model_defaults(self, command_type: str = "default") -> ModelParameters:
        """
        Get default model parameters for command type.
        
        Args:
            command_type: Type of command
            
        Returns:
            ModelParameters with defaults
        """
        # Check for stored model args (backward compatibility)
        stored_args = self._config_cache.get('model_args', {})
        
        # Default parameters from original q.py
        defaults = {
            'model': 'gpt-4.1-mini',
            'max_output_tokens': 1024,
            'temperature': 0.0
        }
        
        # Merge with stored args
        merged = {**defaults, **stored_args}
        
        return ModelParameters(
            model=merged['model'],
            max_output_tokens=merged['max_output_tokens'],
            temperature=merged['temperature'],
            tools=merged.get('tools')
        )
    
    def set_model_defaults(self, command_type: str, params: ModelParameters) -> None:
        """
        Set default model parameters for command type.
        
        Args:
            command_type: Type of command
            params: Model parameters
        """
        # For backward compatibility, save as model_args
        self._config_cache['model_args'] = params.to_dict()
        self._save_config()
    
    def save_conversation(self, messages: List[Message]) -> None:
        """
        Save conversation history.
        
        Args:
            messages: List of conversation messages
        """
        # Convert messages to dict format for backward compatibility
        message_dicts = []
        for msg in messages:
            if isinstance(msg, Message):
                message_dicts.append(msg.to_dict())
            else:
                # Handle legacy format
                message_dicts.append(msg)
        
        self._config_cache['messages'] = message_dicts
        self._save_config()
    
    def load_conversation(self) -> List[Message]:
        """
        Load conversation history.
        
        Returns:
            List of conversation messages
        """
        stored_messages = self._config_cache.get('messages', [])
        messages = []
        
        for msg_data in stored_messages:
            if isinstance(msg_data, dict):
                if 'role' in msg_data and 'content' in msg_data:
                    try:
                        messages.append(Message.from_dict(msg_data))
                    except (ValueError, KeyError):
                        # Handle legacy message format
                        messages.append(msg_data)
                else:
                    # Handle legacy format (image generation, etc.)
                    messages.append(msg_data)
        
        return messages
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self._config_cache['messages'] = []
        self._save_config()
    
    def get_clip_output_setting(self) -> bool:
        """Get clipboard output setting (backward compatibility)."""
        return self._config_cache.get('clip_output', False)
    
    def set_clip_output_setting(self, enabled: bool) -> None:
        """Set clipboard output setting (backward compatibility)."""
        self._config_cache['clip_output'] = enabled
        self._save_config()
    
    def migrate_from_old_format(self) -> bool:
        """
        Migrate from old resources.json format if needed.
        
        Returns:
            True if migration was performed, False if not needed
        """
        # Check if migration is needed
        has_new_format = 'providers' in self._config_cache or 'preferences' in self._config_cache
        has_old_format = any(key in self._config_cache for key in ['openai_key', 'model_args', 'messages'])
        
        if has_old_format and not has_new_format:
            # Perform migration
            if 'openai_key' in self._config_cache:
                self.set_api_key('openai', self._config_cache['openai_key'])
            
            # Set version marker
            self._config_cache['version'] = '2.0'
            self._save_config()
            return True
        
        return False
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        return self._config_cache.get('preferences', {}).copy()


# Global instance for backward compatibility
_default_config = None

def get_default_config() -> ConfigManager:
    """Get the default global configuration instance."""
    global _default_config
    if _default_config is None:
        _default_config = ConfigManager()
    return _default_config


# Backward compatibility functions that match original q.py exactly
def _load_resource(name: str, default: Any) -> Any:
    """Backward compatibility function matching original q.py."""
    return get_default_config()._load_resource(name, default)


def _save_resource(name: str, value: Any) -> None:
    """Backward compatibility function matching original q.py."""
    get_default_config()._save_resource(name, value)