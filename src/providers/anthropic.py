from typing import Any
from ..client import *


class AnthropicClient(TextClient):
    """Anthropic API client."""

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
            # minimal request to validate the key
            test_client.messages.create(
                model=self.AUTH_TEST_MODEL,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
        except Exception as e:
            raise ValueError(f"Anthropic API key validation failed: {e}")

    def _should_retry(self, error: Exception) -> bool:
        # rate limits, connection issues, server errors
        if isinstance(error, (
            self._anthropic.RateLimitError,
            self._anthropic.APIConnectionError,
            self._anthropic.APITimeoutError,
            self._anthropic.InternalServerError
        )):
            return True

        # generic API errors with retryable status codes
        if isinstance(error, self._anthropic.APIStatusError):
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True

        return False

    def _create_async_client(self) -> Any:
        return self._anthropic.AsyncAnthropic(api_key=self.api_key)

    def _convert_model_args(self, model_args: dict) -> dict:
        """Convert generic model args to include required Anthropic fields."""
        if 'max_tokens' not in model_args:
            model_args['max_tokens'] = self.DEFAULT_MAX_TOKENS
        return model_args

    def _convert_messages(self, messages: Messages) -> tuple[str | None, Messages]:
        """Convert generic messages to Anthropic format."""
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                anthropic_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        return system_prompt, anthropic_messages

    async def _generate_text_async(self, messages: Messages, model: str, **model_args) -> str:
        system_prompt, anthropic_messages = self._convert_messages(messages)
        model_args = self._convert_model_args(model_args)

        return (await self._async_client.messages.create(
            messages=anthropic_messages,
            system=system_prompt,
            model=model,
            **model_args
        )).content[0].text
