import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar

from .message import Message


T = TypeVar('T')


MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0
MAX_JITTER = 0.1


class Client(ABC, Generic[T]):
    """Base client for LLM providers."""

    def __init__(self, api_key: str, model: str, **model_args):
        """Initialize client with credentials, model, and optional model args."""
        self.api_key = api_key
        self.model = model
        self.model_args = model_args
        self._import_sdk()
        self._async_client = self._create_async_client()

    async def generate(self, messages: list[Message]) -> T:
        """Generate output with retry logic."""
        return await self._retry(self._generate, messages)

    async def _retry(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with retry logic and exponential backoff."""
        for attempt in range(MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == MAX_RETRIES or not self._should_retry(e):
                    raise
                await asyncio.sleep(self._calc_backoff(attempt))

    def _calc_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        base_delay = BACKOFF_FACTOR ** attempt
        jitter = random.uniform(0, MAX_JITTER * base_delay)
        return base_delay + jitter

    @abstractmethod
    async def _generate(self, messages: list[Message]) -> T:
        """Make API call and return output."""
        pass

    @abstractmethod
    def _import_sdk(self):
        """Import provider SDK lazily to avoid loading unused dependencies."""
        pass

    @abstractmethod
    def _should_retry(self, error: Exception) -> bool:
        """Determine which errors should trigger retry attempt."""
        pass

    @abstractmethod
    def _create_async_client(self) -> Any:
        """Create provider client instance."""
        pass

