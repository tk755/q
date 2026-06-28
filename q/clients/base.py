import asyncio
import random
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    model_config = ConfigDict(ser_json_bytes="base64", val_json_bytes="base64")
    role: Role
    text: str
    images: list[bytes] = Field(default_factory=list)


class Client[T](ABC):
    """Stateful base client for LLM providers."""

    # role name mapping
    ROLES: ClassVar[dict[Role, str]]

    # retry configuration
    MAX_RETRIES = 5
    BACKOFF_FACTOR = 2.0
    MAX_JITTER = 0.1

    def __init__(self, api_key: str, model: str, messages: list[Message] | None = None, system: str | None = None, **model_args):
        self.api_key = api_key
        self.model = model
        self.model_args = model_args
        self.messages = messages.copy() if messages else []
        self.system = system
        self._async_client = self._create_async_client(api_key)

    async def generate(self, prompt: str, system: str | None = None, images: list[bytes] | None = None) -> T:
        """Generate a response and update conversation state and system prompt if provided. Use `""` to clear the system prompt."""
        if system is not None:
            self.system = system or None
        self.messages.append(Message(role=Role.USER, text=prompt, images=images or []))
        output = await self._generate(self.messages, self.system)
        if isinstance(output, str):
            self.messages.append(Message(role=Role.ASSISTANT, text=output))
        elif isinstance(output, bytes):
            self.messages.append(Message(role=Role.ASSISTANT, text="", images=[output]))
        elif isinstance(output, list) and all(isinstance(item, bytes) for item in output):
            self.messages.append(Message(role=Role.ASSISTANT, text="", images=output))
        else:
            raise TypeError(f"unexpected output type: {type(output).__name__}")
        return output

    async def batch_generate(self, prompt_list: list[str], system: str | None = None, images: list[bytes] | None = None, n_threads: int = 8) -> list[T]:
        """Concurrently generate a response to each input with the current history; *does not update state*."""
        system = system if system is not None else self.system
        semaphore = asyncio.Semaphore(n_threads)

        async def process(prompt: str) -> T:
            async with semaphore:
                return await self._generate([*self.messages, Message(role=Role.USER, text=prompt, images=images or [])], system)

        return await asyncio.gather(*(process(prompt) for prompt in prompt_list))

    def drop_exchanges(self, n: int = 1) -> None:
        """Drop the last `n` exchanges (a user message and the responses after it)."""
        if n <= 0:
            return
        count = 0
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].role == Role.USER:
                count += 1
                if count == n:
                    self.messages = self.messages[:i]
                    break

    async def _generate(self, messages: list[Message], system: str | None) -> T:
        """Format messages, inject model args, send the request with retries, and extract the output."""
        formatted_messages = [self._format_message(message) for message in messages]
        response = await self._retry(self._request, formatted_messages, system, self._inject_args(self.model_args))
        return self._extract_output(response)

    async def _retry(self, func: Callable[..., Awaitable[T]], *args: Any) -> T:
        """Call an async func with exponential backoff on transient errors."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await func(*args)
            except Exception as e:
                if attempt == self.MAX_RETRIES or not self._should_retry(e):
                    raise
                await asyncio.sleep(self._calc_backoff(attempt))

    def _calc_backoff(self, attempt: int) -> float:
        """Calculate the exponential backoff delay with jitter for a retry attempt."""
        base_delay = self.BACKOFF_FACTOR**attempt
        jitter = random.uniform(0, self.MAX_JITTER * base_delay)
        return base_delay + jitter

    @staticmethod
    def _sniff_mime(data: bytes) -> str:
        """Detect an image's MIME type from its magic bytes."""
        if data.startswith(b"\x89PNG"):
            return "image/png"
        if data.startswith(b"\xff\xd8"):
            return "image/jpeg"
        if data.startswith(b"GIF8"):
            return "image/gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        raise ValueError("unrecognized image format")

    @classmethod
    def _inject_args(cls, model_args: dict) -> dict:
        """Adjust the model args before a request; never mutates input."""
        return model_args

    @staticmethod
    @abstractmethod
    def _create_async_client(api_key: str) -> Any:
        """Import the provider SDK and create its async client instance."""

    @staticmethod
    @abstractmethod
    def _should_retry(error: Exception) -> bool:
        """Determine whether an error should trigger a retry."""

    @classmethod
    @abstractmethod
    def _format_message(cls, message: Message) -> dict:
        """Format a single message into the provider's request format."""

    @abstractmethod
    async def _request(self, formatted_messages: list[dict], system: str | None, model_args: dict) -> Any:
        """Send the formatted messages, system prompt, and model args to the provider and return the raw response."""

    @staticmethod
    @abstractmethod
    def _extract_output(response: Any) -> T:
        """Extract the output value from a provider response."""
