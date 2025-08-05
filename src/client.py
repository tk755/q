import time
import random
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable

# Type aliases
Messages = list[dict[str, str]]

# Retry configuration defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 2.0
JITTER_PERCENTAGE = 0.1  # 10% jitter for exponential backoff


class BaseClient(ABC):
    """
    Base client for LLM providers with automatic retry logic.
    
    Subclasses implement provider-specific authentication, API calls, and response parsing.
    The base class handles retry logic with exponential backoff automatically.
    """
    
    def __init__(self, max_retries: int = DEFAULT_MAX_RETRIES, backoff_factor: float = DEFAULT_BACKOFF_FACTOR):
        """Initialize client with retry configuration."""
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._sync_client = None
        self._async_client = None
    
    def _calc_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        base_delay = self.backoff_factor ** attempt
        jitter = random.uniform(0, JITTER_PERCENTAGE * base_delay)
        return base_delay + jitter
    
    def _retry_wrapper(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with retry logic and exponential backoff."""
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries or not self._should_retry(e):
                    raise e
                
                time.sleep(self._calc_backoff(attempt))
    
    async def _async_retry_wrapper(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute async function with retry logic and exponential backoff."""
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries or not self._should_retry(e):
                    raise e
                
                # Async sleep with backoff
                await asyncio.sleep(self._calc_backoff(attempt))
    
    def prompt(self, messages: Messages, model: str, **kwargs) -> str:
        """Generate text response synchronously with automatic retry logic."""
        def _make_request():
            if self._sync_client is None:
                self._sync_client = self._create_sync_client()
            
            response = self._prompt_sync(messages, model, **kwargs)
            return self._extract_text(response)
        
        return self._retry_wrapper(_make_request)

    
    async def prompt_async(self, messages: Messages, model: str, **kwargs) -> str:
        """Generate text response asynchronously with automatic retry logic."""
        async def _make_request():
            if self._async_client is None:
                self._async_client = self._create_async_client()
            
            response = await self._prompt_async(messages, model, **kwargs)
            return self._extract_text(response)
        
        return await self._async_retry_wrapper(_make_request)
        
    @abstractmethod
    def _should_retry(self, error: Exception) -> bool:
        """Determine if error should trigger retry attempt."""
        pass
    
    @abstractmethod
    def _create_sync_client(self):
        """Create provider's synchronous client instance."""
        pass
    
    @abstractmethod
    def _create_async_client(self):
        """Create provider's asynchronous client instance."""
        pass
    
    @abstractmethod
    def _prompt_sync(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make synchronous API call and return raw response."""
        pass
    
    @abstractmethod
    async def _prompt_async(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make asynchronous API call and return raw response."""
        pass
    
    @abstractmethod
    def _extract_text(self, response: Any) -> str:
        """Extract text content from provider's API response."""
        pass


class OpenAIClient(BaseClient):
    """OpenAI API client with authentication and retry logic."""
    
    def __init__(self, api_key: str, max_retries: int = DEFAULT_MAX_RETRIES, backoff_factor: float = DEFAULT_BACKOFF_FACTOR):
        """Initialize OpenAI client with API key validation."""
        super().__init__(max_retries, backoff_factor)
        self.api_key = api_key
        
        try:
             # Lazy import to avoid dependency if not used
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI client requires 'openai' package. "
                "Install with: pip install openai"
            )
        
        self._openai = openai
        
        # Validate authentication immediately
        self._validate_auth()
    
    def _validate_auth(self):
        """Validate API key with test request to models endpoint."""
        try:
            test_client = self._openai.OpenAI(api_key=self.api_key)
            # Make a minimal request to validate the key
            test_client.models.list()
        except Exception as e:
            raise ValueError(f"OpenAI authentication failed: {e}")
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if OpenAI error should trigger retry attempt."""
        # Rate limit errors - retry
        if isinstance(error, self._openai.RateLimitError):
            return True
        
        # API connection errors - retry
        if isinstance(error, (self._openai.APIConnectionError, self._openai.APITimeoutError)):
            return True
        
        # Internal server errors - retry
        if isinstance(error, self._openai.InternalServerError):
            return True
        
        # For generic APIStatusError, check status code
        if isinstance(error, self._openai.APIStatusError):
            # 429 (rate limit), 500s (server errors) are retryable
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True
        
        return False
    
    def _create_sync_client(self):
        """Create synchronous OpenAI client instance."""
        return self._openai.OpenAI(api_key=self.api_key)
    
    def _create_async_client(self):
        """Create asynchronous OpenAI client instance."""
        return self._openai.AsyncOpenAI(api_key=self.api_key)
    
    def _prompt_sync(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make synchronous chat completion request to OpenAI."""
        return self._sync_client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )
    
    async def _prompt_async(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make asynchronous chat completion request to OpenAI."""
        return await self._async_client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )
    
    def _extract_text(self, response: Any) -> str:
        """Extract text content from OpenAI chat completion response."""
        return response.choices[0].message.content


class AnthropicClient(BaseClient):
    """Anthropic Claude API client with authentication and retry logic."""
    
    # Anthropic-specific constants
    AUTH_TEST_MODEL = "claude-3-haiku-20240307"
    DEFAULT_MAX_TOKENS = 1024
    
    def __init__(self, api_key: str, max_retries: int = DEFAULT_MAX_RETRIES, backoff_factor: float = DEFAULT_BACKOFF_FACTOR):
        """Initialize Anthropic client with API key validation."""
        super().__init__(max_retries, backoff_factor)
        self.api_key = api_key
        
        try:
             # Lazy import to avoid dependency if not used
            import anthropic
        except ImportError:
            raise ImportError(
                "Anthropic client requires 'anthropic' package. "
                "Install with: pip install anthropic"
            )
        
        self._anthropic = anthropic
        
        # Validate authentication immediately
        self._validate_auth()
    
    def _validate_auth(self):
        """Validate API key with minimal test message request."""
        try:
            test_client = self._anthropic.Anthropic(api_key=self.api_key)
            # Make a minimal request to validate the key
            # Anthropic doesn't have a models endpoint, so we'll use a minimal message
            test_client.messages.create(
                model=self.AUTH_TEST_MODEL,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
        except Exception as e:
            raise ValueError(f"Anthropic authentication failed: {e}")
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if Anthropic error should trigger retry attempt."""
        # Rate limit errors - retry
        if isinstance(error, self._anthropic.RateLimitError):
            return True
        
        # API connection errors - retry
        if isinstance(error, (self._anthropic.APIConnectionError, self._anthropic.APITimeoutError)):
            return True
        
        # Internal server errors - retry
        if isinstance(error, self._anthropic.InternalServerError):
            return True
        
        # For generic APIStatusError, check status code
        if isinstance(error, self._anthropic.APIStatusError):
            # 429 (rate limit), 500s (server errors) are retryable
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True
        
        return False
    
    def _prepare_anthropic_kwargs(self, kwargs: dict) -> dict:
        """Add Anthropic-specific defaults like max_tokens to request."""
        if 'max_tokens' not in kwargs:
            kwargs = kwargs.copy()  # Don't mutate original
            kwargs['max_tokens'] = self.DEFAULT_MAX_TOKENS
        return kwargs
    
    def _convert_messages(self, messages: Messages) -> tuple[str | None, Messages]:
        """Convert OpenAI message format to Anthropic's system/messages format."""
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                anthropic_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        return system_message, anthropic_messages
    
    def _create_sync_client(self):
        """Create synchronous Anthropic client instance."""
        return self._anthropic.Anthropic(api_key=self.api_key)
    
    def _create_async_client(self):
        """Create asynchronous Anthropic client instance."""
        return self._anthropic.AsyncAnthropic(api_key=self.api_key)
    
    def _prompt_sync(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make synchronous message request to Anthropic Claude."""
        system_message, anthropic_messages = self._convert_messages(messages)
        kwargs = self._prepare_anthropic_kwargs(kwargs)
        
        return self._sync_client.messages.create(
            messages=anthropic_messages,
            model=model,
            system=system_message,
            **kwargs
        )
    
    async def _prompt_async(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make asynchronous message request to Anthropic Claude."""
        system_message, anthropic_messages = self._convert_messages(messages)
        kwargs = self._prepare_anthropic_kwargs(kwargs)
        
        return await self._async_client.messages.create(
            messages=anthropic_messages,
            model=model,
            system=system_message,
            **kwargs
        )
    
    def _extract_text(self, response: Any) -> str:
        """Extract text content from Anthropic message response."""
        return response.content[0].text
