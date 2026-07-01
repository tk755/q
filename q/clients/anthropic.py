import base64
from typing import Any, ClassVar

from .base import Client, Message, Role

__all__ = ["TextClient", "WebClient"]


class AnthropicClient[T](Client[T]):
    """Base client for the Anthropic Messages API."""

    ROLES: ClassVar[dict[Role, str]] = {Role.USER: "user", Role.ASSISTANT: "assistant"}
    SPOOF_ASSISTANT_IMAGES = True
    DEFAULT_MAX_TOKENS = 16384

    @staticmethod
    def _create_async_client(api_key: str) -> Any:
        import anthropic
        return anthropic.AsyncAnthropic(api_key=api_key)

    @staticmethod
    def _should_retry(error: Exception) -> bool:
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
        content = []
        for image in message.images:
            source = {"type": "base64", "media_type": cls._sniff_mime(image), "data": base64.b64encode(image).decode()}
            content.append({"type": "image", "source": source})
        if message.text:
            content.append({"type": "text", "text": message.text})
        return {"role": cls.ROLES[message.role], "content": content}

    async def _request(self, formatted_messages: list[dict], system: str | None, model_args: dict) -> Any:
        """Send a request to the Messages API."""
        kwargs = {"model": self.model, "messages": formatted_messages, **model_args}
        if system:
            kwargs["system"] = system
        return await self._async_client.messages.create(**kwargs)

    @staticmethod
    def _extract_output(response: Any) -> T:
        """Extract the text output from a Messages API response, after any tool-use blocks."""
        content = response.content
        last_tool = max((i for i, block in enumerate(content) if block.type != "text"), default=-1)
        return "".join(block.text for block in content[last_tool + 1:] if block.type == "text")


class TextClient(AnthropicClient[str]): ...


class WebClient(AnthropicClient[str]):
    @classmethod
    def _inject_args(cls, model_args: dict) -> dict:
        """Add the web-search tool, merging with any existing tools."""
        model_args = super()._inject_args(model_args)
        tools = model_args.get("tools", [])
        if not any(tool.get("name") == "web_search" for tool in tools):
            tools = [*tools, {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
        return {**model_args, "tools": tools}
