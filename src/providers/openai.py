from typing import Any
from ..client import *


class OpenAIClient(TextClient, ImageClient, ToolClient, RAGClient):
    """OpenAI API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        super().__init__()

    def _import_sdk(self):
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI client requires 'openai' package.")
        self._openai = openai

    def _validate_auth(self):
        try:
            test_client = self._openai.OpenAI(api_key=self.api_key)
            # Make a minimal request to validate the key
            test_client.models.list()
        except Exception as e:
            raise ValueError(f"OpenAI API key validation failed: {e}")

    def _create_async_client(self) -> Any:
        return self._openai.AsyncOpenAI(api_key=self.api_key)

    def _should_retry(self, error: Exception) -> bool:
        # Rate limit errors
        if isinstance(error, self._openai.RateLimitError):
            return True

        # API connection errors
        if isinstance(error, (self._openai.APIConnectionError, self._openai.APITimeoutError)):
            return True

        # Internal server errors
        if isinstance(error, self._openai.InternalServerError):
            return True

        # For generic APIStatusError, check status code
        if isinstance(error, self._openai.APIStatusError):
            # 429 (rate limit), 500s (server errors) are retryable
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True

        return False

    async def _generate_text_async(self, messages: Messages, model: str, **kwargs) -> Any:
        return await self._async_client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )

    def _extract_text(self, response: Any) -> str:
        return response.choices[0].message.content

    async def _generate_image_async(self, messages: Messages, model: str, **kwargs) -> Any:
        raise NotImplementedError("Image generation not yet implemented")

    async def _edit_image_async(self, messages: Messages, model: str, **kwargs) -> Any:
        raise NotImplementedError("Image editing not yet implemented")

    def _extract_image(self, response: Any) -> bytes:
        raise NotImplementedError("Image extraction not yet implemented")

    async def _tool_call_async(self, messages: Messages, tools: list[dict], model: str, **kwargs) -> Any:
        raise NotImplementedError("Tool calling not yet implemented")

    def _extract_tool_call(self, response: Any) -> list[dict]:
        raise NotImplementedError("Tool call extraction not yet implemented")

    async def _search_async(self, messages: Messages, model: str, **kwargs) -> Any:
        raise NotImplementedError("RAG search not yet implemented")

    def _extract_search_results(self, response: Any) -> str:
        raise NotImplementedError("Search result extraction not yet implemented")
