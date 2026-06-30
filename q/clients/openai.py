import base64
from typing import Any, ClassVar

from .base import Client, Message, Role

__all__ = ["ImageClient", "TextClient", "WebClient"]


class OpenAIClient[T](Client[T]):
    """Base client for the OpenAI Responses API."""

    ROLES: ClassVar[dict[Role, str]] = {Role.USER: "user", Role.ASSISTANT: "assistant"}
    SPOOF_ASSISTANT_IMAGES = True

    @staticmethod
    def _create_async_client(api_key: str) -> Any:
        import openai
        return openai.AsyncOpenAI(api_key=api_key)

    @staticmethod
    def _should_retry(error: Exception) -> bool:
        import openai
        if isinstance(error, openai.APIConnectionError):  # includes timeouts
            return True
        if isinstance(error, openai.APIStatusError):
            return error.status_code == 429 or 500 <= error.status_code < 600
        return False

    @classmethod
    def _format_message(cls, message: Message) -> dict:
        """Format a single message into Responses API format."""
        text_type = "output_text" if message.role == Role.ASSISTANT else "input_text"
        content = [{"type": text_type, "text": message.text}] if message.text else []
        for image in message.images:
            data_url = f"data:{cls._sniff_mime(image)};base64,{base64.b64encode(image).decode()}"
            content.append({"type": "input_image", "detail": "auto", "image_url": data_url})
        return {"role": cls.ROLES[message.role], "content": content}

    async def _request(self, formatted_messages: list[dict], system: str | None, model_args: dict) -> Any:
        """Send a request to the Responses API."""
        kwargs = {"model": self.model, "input": formatted_messages, **model_args}
        if system:
            kwargs["input"] = [{"role": "system", "content": system}, *formatted_messages]
        return await self._async_client.responses.create(**kwargs)

    @staticmethod
    def _extract_output(response: Any) -> T:
        """Extract the text output from a Responses API response."""
        return response.output_text


class TextClient(OpenAIClient[str]): ...


class WebClient(OpenAIClient[str]):
    @classmethod
    def _inject_args(cls, model_args: dict) -> dict:
        """Add the web-search tool, merging with any existing tools."""
        model_args = super()._inject_args(model_args)
        tools = model_args.get("tools", [])
        if not any(tool.get("type") == "web_search" for tool in tools):
            tools = [*tools, {"type": "web_search", "search_context_size": "low"}]
        return {**model_args, "tools": tools}


class ImageClient(OpenAIClient[bytes]):
    @classmethod
    def _inject_args(cls, model_args: dict) -> dict:
        """Add the image-generation tool, merging with any existing tools."""
        model_args = super()._inject_args(model_args)
        tools = model_args.get("tools", [])
        if not any(tool.get("type") == "image_generation" for tool in tools):
            tools = [*tools, {"type": "image_generation"}]
        return {**model_args, "tools": tools}

    @staticmethod
    def _extract_output(response: Any) -> bytes:
        """Extract the generated image bytes from the response."""
        for output in response.output:
            if output.type == "image_generation_call":
                return base64.b64decode(output.result)
        raise ValueError("no image_generation_call found")
