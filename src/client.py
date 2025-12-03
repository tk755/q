import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Callable


# Type aliases
Messages = list[dict[str, str]]


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
                    raise e

                time.sleep(self._calc_backoff(attempt))

    async def _async_retry_wrapper(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute async function with retry logic and exponential backoff."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.MAX_RETRIES or not self._should_retry(e):
                    raise e

                # Async sleep with backoff
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
    def _create_async_client(self) -> Any:
        """Create provider's async client instance."""
        pass

    @abstractmethod
    def _should_retry(self, error: Exception) -> bool:
        """Determine which errors should trigger retry attempt."""
        pass


class TextClient(BaseClient):
    """Base client for text generation."""

    def __init__(self):
        super().__init__()

    def generate_text(self, messages: Messages, model: str, **kwargs) -> str:
        """Generate text with retry logic."""
        return asyncio.run(self.generate_text_async(messages, model, **kwargs))

    async def generate_text_async(self, messages: Messages, model: str, **kwargs) -> str:
        """Generate text asynchronously with retry logic."""
        async def _make_request():
            response = await self._generate_text_async(messages, model, **kwargs)
            return self._extract_text(response)
        return await self._async_retry_wrapper(_make_request)

    @abstractmethod
    async def _generate_text_async(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make asynchronous text generation API call and return response."""
        pass

    @abstractmethod
    def _extract_text(self, response: Any) -> str:
        """Extract text content from provider's API response."""
        pass


class ImageClient(BaseClient):
    """Base client for image generation and editing."""

    def generate_image(self, messages: Messages, model: str, **kwargs) -> bytes:
        """Generate image with retry logic."""
        return asyncio.run(self.generate_image_async(messages, model, **kwargs))

    async def generate_image_async(self, messages: Messages, model: str, **kwargs) -> bytes:
        """Generate image asynchronously with retry logic."""
        async def _make_request():
            response = await self._generate_image_async(messages, model, **kwargs)
            return self._extract_image(response)
        return await self._async_retry_wrapper(_make_request)
    
    def edit_image(self, messages: Messages, model: str, **kwargs) -> bytes:
        """Edit image with retry logic."""
        return asyncio.run(self.edit_image_async(messages, model, **kwargs))

    async def edit_image_async(self, messages: Messages, model: str, **kwargs) -> bytes:
        """Edit image asynchronously with retry logic."""
        async def _make_request():
            response = await self._edit_image_async(messages, model, **kwargs)
            return self._extract_image(response)
        return await self._async_retry_wrapper(_make_request)

    @abstractmethod
    async def _generate_image_async(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make asynchronous image generation API call and return response."""
        pass

    @abstractmethod
    async def _edit_image_async(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make asynchronous image edit API call and return response."""
        pass

    @abstractmethod
    def _extract_image(self, response: Any) -> bytes:
        """Extract image from provider's API response."""
        pass


class ToolClient(BaseClient):
    """Base client for tool calling."""

    def tool_call(self, messages: Messages, tools: list[dict], model: str, **kwargs) -> tuple[str, list[dict]]:
        """Generate response with tool calls using retry logic."""
        return asyncio.run(self.tool_call_async(messages, tools, model, **kwargs))

    async def tool_call_async(self, messages: Messages, tools: list[dict], model: str, **kwargs) -> tuple[str, list[dict]]:
        """Generate response with tool calls asynchronously with retry logic."""
        async def _make_request():
            response = await self._tool_call_async(messages, tools, model, **kwargs)
            text = self._extract_text(response)
            tool_calls = self._extract_tool_call(response)
            return text, tool_calls
        return await self._async_retry_wrapper(_make_request)

    @abstractmethod
    async def _tool_call_async(self, messages: Messages, tools: list[dict], model: str, **kwargs) -> Any:
        """Make asynchronous tool-calling API call and return response."""
        pass

    @abstractmethod
    def _extract_tool_call(self, response: Any) -> list[dict]:
        """Extract tool calls from provider's API response."""
        pass


class RAGClient(BaseClient):
    """Base client for retrieval-augmented generation."""

    def search(self, messages: Messages, model: str, **kwargs) -> str:
        """Search and retrieve context with retry logic."""
        return asyncio.run(self.search_async(messages, model, **kwargs))

    async def search_async(self, messages: Messages, model: str, **kwargs) -> str:
        """Search and retrieve context asynchronously with retry logic."""
        async def _make_request():
            response = await self._search_async(messages, model, **kwargs)
            return self._extract_search_results(response)
        return await self._async_retry_wrapper(_make_request)

    @abstractmethod
    async def _search_async(self, messages: Messages, model: str, **kwargs) -> Any:
        """Make asynchronous RAG-search API call and return response."""
        pass

    @abstractmethod
    def _extract_search_results(self, response: Any) -> str:
        """Extract search results from provider's API response."""
        pass
