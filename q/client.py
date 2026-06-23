import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any

from .message import Message


class Client[T](ABC):
    """Base client for LLM providers."""

    # retry configuration
    MAX_RETRIES = 5
    BACKOFF_FACTOR = 2.0
    MAX_JITTER = 0.1

    def __init__(self, api_key: str, model: str, **model_args):
        self.api_key = api_key
        self.model = model
        self.model_args = model_args
        self._import_sdk()
        self._async_client = self._create_async_client()

    async def generate(self, messages: list[Message]) -> T:
        """Generate output with retry logic."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await self._generate(messages)
            except Exception as e:
                if attempt == self.MAX_RETRIES or not self._should_retry(e):
                    raise
                await asyncio.sleep(self._calc_backoff(attempt))

    def _calc_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        base_delay = self.BACKOFF_FACTOR**attempt
        jitter = random.uniform(0, self.MAX_JITTER * base_delay)
        return base_delay + jitter

    @abstractmethod
    def _import_sdk(self) -> None:
        """Import provider SDK lazily to avoid loading unused dependencies."""

    @abstractmethod
    def _should_retry(self, error: Exception) -> bool:
        """Determine which errors should trigger retry attempt."""

    @abstractmethod
    def _create_async_client(self) -> Any:
        """Create provider client instance."""

    @abstractmethod
    async def _generate(self, messages: list[Message]) -> T:
        """Make API call and return output."""
