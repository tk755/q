from typing import Any, ClassVar

from .base import Client, Message, Role

__all__ = ["TextClient"]


class AnthropicClient[T](Client[T]):
    """Base client for the Anthropic Messages API."""

    ROLES: ClassVar[dict[Role, str]] = {Role.USER: "user", Role.ASSISTANT: "assistant"}
    DEFAULT_MAX_TOKENS = 1024

    @classmethod
    def _create_async_client(cls, api_key: str) -> Any:
        import anthropic
        return anthropic.AsyncAnthropic(api_key=api_key)

    @classmethod
    def _should_retry(cls, error: Exception) -> bool:
        import anthropic
        if isinstance(error, anthropic.APIConnectionError):  # includes timeouts
            return True
        if isinstance(error, anthropic.APIStatusError):
            return error.status_code == 429 or 500 <= error.status_code < 600
        return False

    @classmethod
    def _inject_args(cls, model_args: dict) -> dict:
        """Set the default max_tokens if missing."""
        return {"max_tokens": cls.DEFAULT_MAX_TOKENS, **super()._inject_args(model_args)}

    @classmethod
    def _format_message(cls, message: Message) -> dict:
        """Format a single message into Messages API format."""
        return {"role": cls.ROLES[message.role], "content": message.content}

    async def _request(self, formatted_messages: list[dict], system: str | None, model_args: dict) -> Any:
        """Send a request to the Messages API."""
        kwargs = {"model": self.model, "messages": formatted_messages, **model_args}
        if system:
            kwargs["system"] = system
        return await self._async_client.messages.create(**kwargs)

    @classmethod
    def _extract_output(cls, response: Any) -> T:
        """Join the text blocks of a Messages API response."""
        return "".join(block.text for block in response.content if block.type == "text")


class TextClient(AnthropicClient[str]): ...
