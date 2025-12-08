from typing import Any, TypeVar

from ..client import Client
from ..message import Message, Role


T = TypeVar('T')


class AnthropicClient(Client[T]):
    """Base client for Anthropic API."""

    DEFAULT_MAX_TOKENS = 1024

    def _import_sdk(self):
        import anthropic
        self._anthropic = anthropic

    def _should_retry(self, error: Exception) -> bool:
        if isinstance(error, (
            self._anthropic.RateLimitError,
            self._anthropic.APIConnectionError,
            self._anthropic.APITimeoutError,
            self._anthropic.InternalServerError
        )):
            return True

        if isinstance(error, self._anthropic.APIStatusError):
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True

        return False

    def _create_async_client(self) -> Any:
        return self._anthropic.AsyncAnthropic(api_key=self.api_key)

    def _default_model_args(self) -> dict:
        """Get missing model args required by API."""
        args = dict(self.model_args)
        if 'max_tokens' not in args:
            args['max_tokens'] = self.DEFAULT_MAX_TOKENS
        return args

    def _convert_messages(self, messages: list[Message]) -> tuple[str | None, list[dict]]:
        """Convert Message objects to API format."""
        system_prompt = None
        api_messages = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_prompt = msg.content
            else:
                api_messages.append(msg.model_dump(include={"role", "content"}))

        return system_prompt, api_messages


class TextClient(AnthropicClient[str]):
    """Anthropic text generation client."""

    async def _generate(self, messages: list[Message]) -> str:
        system_prompt, api_messages = self._convert_messages(messages)

        response = await self._async_client.messages.create(
            messages=api_messages,
            system=system_prompt,
            model=self.model,
            **self._default_model_args()
        )
        return response.content[0].text
