from typing import Any
from ..client import *


class AnthropicClient(TextClient, ImageClient, ToolClient):
    """Anthropic API client."""

    # Anthropic-specific constants
    AUTH_TEST_MODEL = "claude-3-haiku-20240307"
    DEFAULT_MAX_TOKENS = 1024

    def __init__(self, api_key: str):
        self.api_key = api_key
        super().__init__()

    def _import_sdk(self):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Anthropic client requires 'anthropic' package.")
        self._anthropic = anthropic

    def _validate_auth(self):
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
            raise ValueError(f"Anthropic API key validation failed: {e}")

    def _create_async_client(self) -> Any:
        return self._anthropic.AsyncAnthropic(api_key=self.api_key)

    def _should_retry(self, error: Exception) -> bool:
        # Rate limit errors
        if isinstance(error, self._anthropic.RateLimitError):
            return True

        # API connection errors
        if isinstance(error, (self._anthropic.APIConnectionError, self._anthropic.APITimeoutError)):
            return True

        # Internal server errors
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
        """Convert Messages type to Anthropic's system/messages format."""
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

    async def _generate_text_async(self, messages: Messages, model: str, **kwargs) -> Any:
        system_message, anthropic_messages = self._convert_messages(messages)
        kwargs = self._prepare_anthropic_kwargs(kwargs)

        return await self._async_client.messages.create(
            messages=anthropic_messages,
            model=model,
            system=system_message,
            **kwargs
        )

    def _extract_text(self, response: Any) -> str:
        return response.content[0].text

    # ImageClient abstract method stubs
    async def _generate_image_async(self, messages: Messages, model: str, **kwargs) -> Any:
        raise NotImplementedError("Image generation not yet implemented")

    async def _edit_image_async(self, messages: Messages, model: str, **kwargs) -> Any:
        raise NotImplementedError("Image editing not yet implemented")

    def _extract_image(self, response: Any) -> bytes:
        raise NotImplementedError("Image extraction not yet implemented")

    # ToolClient abstract method stubs
    async def _tool_call_async(self, messages: Messages, tools: list[dict], model: str, **kwargs) -> Any:
        raise NotImplementedError("Tool calling not yet implemented")

    def _extract_tool_call(self, response: Any) -> list[dict]:
        raise NotImplementedError("Tool call extraction not yet implemented")
