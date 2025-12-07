import base64
from typing import Any, TypeVar

from ..client import Client
from ..message import Message


T = TypeVar('T')


class OpenAIClient(Client[T]):
    """Base client for OpenAI API."""

    def _import_sdk(self):
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI client requires 'openai' package.")
        self._openai = openai

    def _should_retry(self, error: Exception) -> bool:
        if isinstance(error, (
            self._openai.RateLimitError,
            self._openai.APIConnectionError,
            self._openai.APITimeoutError,
            self._openai.InternalServerError
        )):
            return True

        if isinstance(error, self._openai.APIStatusError):
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True

        return False

    def _create_async_client(self) -> Any:
        return self._openai.AsyncOpenAI(api_key=self.api_key)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert Message objects to API format."""
        return [msg.model_dump(include={"role", "content"}) for msg in messages]


class TextClient(OpenAIClient[str]):
    """OpenAI text generation client."""

    async def _generate(self, messages: list[Message]) -> str:
        response = await self._async_client.responses.create(
            input=self._convert_messages(messages),
            model=self.model,
            **self.model_args
        )
        return response.output_text


class WebClient(OpenAIClient[str]):
    """OpenAI web search client."""

    DEFAULT_TOOLS = [{'type': 'web_search_preview', 'search_context_size': 'low'}]

    async def _generate(self, messages: list[Message]) -> str:
        args = {'tools': self.DEFAULT_TOOLS, **self.model_args}
        response = await self._async_client.responses.create(
            input=self._convert_messages(messages),
            model=self.model,
            **args
        )
        return response.output_text


class ImageClient(OpenAIClient[bytes]):
    """OpenAI image generation client."""

    DEFAULT_TOOLS = [{'type': 'image_generation', 'size': '1024x1024', 'quality': 'auto'}]

    async def _generate(self, messages: list[Message]) -> bytes:
        args = {'tools': self.DEFAULT_TOOLS, **self.model_args}
        response = await self._async_client.responses.create(
            input=self._convert_messages(messages),
            model=self.model,
            **args
        )
        return self._extract_image(response)

    def _extract_image(self, response: Any) -> bytes:
        for output in response.output:
            if output.type == 'image_generation_call':
                return base64.b64decode(output.result)
        raise ValueError("No image_generation_call found in response output")
