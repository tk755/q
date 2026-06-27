import base64
from typing import Any, ClassVar

from .base import Client, Message, Role

__all__ = ["ImageClient", "TextClient", "WebClient"]


class GeminiClient[T](Client[T]):
    """Base client for the Gemini Interactions API."""

    ROLES: ClassVar[dict[Role, str]] = {Role.USER: "user_input", Role.ASSISTANT: "model_output"}

    @classmethod
    def _create_async_client(cls, api_key: str) -> Any:
        from google import genai
        return genai.Client(api_key=api_key).aio

    @classmethod
    def _should_retry(cls, error: Exception) -> bool:
        from google import genai
        if isinstance(error, genai.errors.APIError):
            code = error.code
            return isinstance(code, int) and (code == 429 or 500 <= code < 600)
        return False

    @classmethod
    def _inject_args(cls, model_args: dict) -> dict:
        """Disable server-side storage by default."""
        return {"store": False, **super()._inject_args(model_args)}

    @classmethod
    def _format_message(cls, message: Message) -> dict:
        """Format a single message into Interactions API format."""
        return {"type": cls.ROLES[message.role], "content": [{"type": "text", "text": message.content}]}

    async def _request(self, formatted_messages: list[dict], system: str | None, model_args: dict) -> Any:
        """Send a request to the Interactions API."""
        kwargs = {"model": self.model, "input": formatted_messages, **model_args}
        if system:
            kwargs["system_instruction"] = system
        return await self._async_client.interactions.create(**kwargs)

    @classmethod
    def _extract_output(cls, response: Any) -> T:
        """Extract the text output from an Interactions API response."""
        return response.output_text


class TextClient(GeminiClient[str]): ...


class WebClient(GeminiClient[str]):
    @classmethod
    def _inject_args(cls, model_args: dict) -> dict:
        """Add the web-search tool, merging with any existing tools."""
        model_args = super()._inject_args(model_args)
        tools = model_args.get("tools", [])
        if not any(tool.get("type") == "google_search" for tool in tools):
            tools = [*tools, {"type": "google_search"}]
        return {**model_args, "tools": tools}


class ImageClient(GeminiClient[bytes]):
    async def _request(self, formatted_messages: list[dict], system: str | None, model_args: dict) -> Any:
        """Send a one-shot image request to the Interactions API using the latest prompt."""
        kwargs = {"model": self.model, "input": formatted_messages[-1]["content"][0]["text"], **model_args}
        if system:
            kwargs["system_instruction"] = system
        return await self._async_client.interactions.create(**kwargs)

    @classmethod
    def _extract_output(cls, response: Any) -> bytes:
        """Extract the generated image bytes from the response."""
        return base64.b64decode(response.output_image.data)
