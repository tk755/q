from typing import Any

from ..core import Client, Message, Role

__all__ = ["TextClient"]


class AnthropicClient[T](Client[T]):
    """Base client for Anthropic API."""

    DEFAULT_MAX_TOKENS = 1024

    def __init__(self, api_key: str, model: str, **model_args):
        model_args.setdefault("max_tokens", self.DEFAULT_MAX_TOKENS)
        super().__init__(api_key, model, **model_args)

    def _import_sdk(self) -> None:
        import anthropic
        self._anthropic = anthropic

    def _should_retry(self, error: Exception) -> bool:
        if isinstance(
            error,
            (
                self._anthropic.RateLimitError,
                self._anthropic.APIConnectionError,
                self._anthropic.APITimeoutError,
                self._anthropic.InternalServerError,
            ),
        ):
            return True

        if isinstance(error, self._anthropic.APIStatusError):
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True

        return False

    def _create_async_client(self) -> Any:
        return self._anthropic.AsyncAnthropic(api_key=self.api_key)

    def _convert_messages(self, messages: list[Message]) -> tuple[list[dict] | None, list[dict]]:
        """Convert Message objects to API format."""
        system_prompt = None
        api_messages = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_prompt = [{"type": "text", "text": msg.content}]
            else:
                api_messages.append(msg.model_dump(include={"role", "content"}))

        return system_prompt, api_messages


class TextClient(AnthropicClient[str]):
    """Anthropic text generation client."""

    async def _generate(self, messages: list[Message]) -> str:
        system_prompt, api_messages = self._convert_messages(messages)

        kwargs = {"messages": api_messages, "model": self.model, **self.model_args}
        if system_prompt is not None:
            kwargs["system"] = system_prompt

        response = await self._async_client.messages.create(**kwargs)
        return "".join(block.text for block in response.content if block.type == "text")
