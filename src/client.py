import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Callable


Messages = list[dict[str, str]]

# region Base Client

class BaseClient(ABC):
    """Base client for LLM providers with authentication validation and retry logic."""

    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2.0
    MAX_JITTER = 0.1

    def __init__(self):
        """Orchestrate client initialization."""
        self._import_sdk()
        self._validate_auth()
        self._async_client = self._create_async_client()

    def _retry_wrapper(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with retry logic and exponential backoff."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.MAX_RETRIES or not self._should_retry(e):
                    raise
                time.sleep(self._calc_backoff(attempt))

    async def _async_retry_wrapper(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute async function with retry logic and exponential backoff."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.MAX_RETRIES or not self._should_retry(e):
                    raise
                await asyncio.sleep(self._calc_backoff(attempt))

    def _calc_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        base_delay = self.BACKOFF_FACTOR ** attempt
        jitter = random.uniform(0, self.MAX_JITTER * base_delay)
        return base_delay + jitter

    @abstractmethod
    def _import_sdk(self):
        """Import provider SDK lazily to avoid loading unused dependencies."""
        pass

    @abstractmethod
    def _validate_auth(self):
        """Validate API credentials with minimal test request."""
        pass

    @abstractmethod
    def _should_retry(self, error: Exception) -> bool:
        """Determine which errors should trigger retry attempt."""
        pass

    @abstractmethod
    def _create_async_client(self) -> Any:
        """Create provider's async client instance."""
        pass

# region Text Client

class TextClient(BaseClient):
    """Base client for text generation."""

    def __init__(self):
        super().__init__()

    def generate_text(self, messages: Messages, model: str, **model_args) -> str:
        """Generate text with retry logic."""
        return asyncio.run(self.generate_text_async(messages, model, **model_args))

    async def generate_text_async(self, messages: Messages, model: str, **model_args) -> str:
        """Generate text asynchronously with retry logic."""
        async def _make_request():
            return await self._generate_text_async(messages, model, **model_args)
        return await self._async_retry_wrapper(_make_request)

    @abstractmethod
    async def _generate_text_async(self, messages: Messages, model: str, **model_args) -> str:
        """Make asynchronous text generation API call and return text."""
        pass

# region Image Client

class ImageClient(BaseClient):
    """Base client for image generation and editing."""

    def generate_image(self, messages: Messages, model: str, **model_args) -> bytes:
        """Generate image with retry logic."""
        return asyncio.run(self.generate_image_async(messages, model, **model_args))

    async def generate_image_async(self, messages: Messages, model: str, **model_args) -> bytes:
        """Generate image asynchronously with retry logic."""
        async def _make_request():
            return await self._generate_image_async(messages, model, **model_args)
        return await self._async_retry_wrapper(_make_request)

    def edit_image(self, messages: Messages, model: str, **model_args) -> bytes:
        """Edit image with retry logic."""
        return asyncio.run(self.edit_image_async(messages, model, **model_args))

    async def edit_image_async(self, messages: Messages, model: str, **model_args) -> bytes:
        """Edit image asynchronously with retry logic."""
        async def _make_request():
            return await self._edit_image_async(messages, model, **model_args)
        return await self._async_retry_wrapper(_make_request)

    @abstractmethod
    async def _generate_image_async(self, messages: Messages, model: str, **model_args) -> bytes:
        """Make asynchronous image generation API call and return image."""
        pass

    @abstractmethod
    async def _edit_image_async(self, messages: Messages, model: str, **model_args) -> bytes:
        """Make asynchronous image edit API call and return image."""
        pass

# region Web Client

class WebClient(BaseClient):
    """Base client for web-search."""

    def web_search(self, messages: Messages, model: str, **model_args) -> str:
        """Perform web search with retry logic."""
        return asyncio.run(self.web_search_async(messages, model, **model_args))

    async def web_search_async(self, messages: Messages, model: str, **model_args) -> str:
        """Perform web search asynchronously with retry logic."""
        async def _make_request():
            return await self._web_search_async(messages, model, **model_args)
        return await self._async_retry_wrapper(_make_request)

    @abstractmethod
    async def _web_search_async(self, messages: Messages, model: str, **model_args) -> str:
        """Make asynchronous web-search API call and return text."""
        pass
