import base64
from typing import Any, TypeVar

from ..client import Client
from ..message import Message

T = TypeVar("T")


class OpenAIClient(Client[T]):
    """Base client for OpenAI API."""

    def _import_sdk(self):
        import openai

        self._openai = openai

    def _should_retry(self, error: Exception) -> bool:
        if isinstance(
            error,
            (
                self._openai.RateLimitError,
                self._openai.APIConnectionError,
                self._openai.APITimeoutError,
                self._openai.InternalServerError,
            ),
        ):
            return True

        if isinstance(error, self._openai.APIStatusError):
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True

        return False

    def _create_async_client(self) -> Any:
        return self._openai.AsyncOpenAI(api_key=self.api_key)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        return [msg.model_dump(include={"role", "content"}) for msg in messages]

    @property
    def tools(self) -> list[dict] | None:
        return None

    async def _generate(self, messages: list[Message]) -> T:
        response = await self._async_client.responses.create(
            input=self._convert_messages(messages),
            model=self.model,
            tools=self.tools,
            **self.model_args,
        )
        return self._extract(response)

    def _extract(self, response: Any) -> T:
        return response.output_text


class TextClient(OpenAIClient[str]): ...


class WebClient(OpenAIClient[str]):
    def __init__(self, api_key: str, model: str, *, search_context_size: str = "low", **model_args):
        self._search_context_size = search_context_size
        super().__init__(api_key, model, **model_args)

    @property
    def tools(self) -> list[dict]:
        return [{"type": "web_search_preview", "search_context_size": self._search_context_size}]


class ImageClient(OpenAIClient[bytes]):
    def __init__(self, api_key: str, model: str, *, size: str = "1024x1024", quality: str = "auto", **model_args):
        self._size = size
        self._quality = quality
        super().__init__(api_key, model, **model_args)

    @property
    def tools(self) -> list[dict]:
        return [{"type": "image_generation", "size": self._size, "quality": self._quality}]

    def _extract(self, response: Any) -> bytes:
        for output in response.output:
            if output.type == "image_generation_call":
                return base64.b64decode(output.result)
        raise ValueError("No image_generation_call found")
