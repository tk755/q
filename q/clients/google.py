import base64
from typing import Any

from ..core import Client, Message, Role

__all__ = ["ImageClient", "TextClient", "WebClient"]

ROLE_MAP = {Role.USER: "user_input", Role.ASSISTANT: "model_output"}


class GeminiClient[T](Client[T]):
    """Base client for the Gemini Interactions API."""

    def _import_sdk(self) -> None:
        from google import genai
        self._genai = genai

    def _should_retry(self, error: Exception) -> bool:
        if isinstance(error, self._genai.errors.APIError):
            code = error.code
            return isinstance(code, int) and (code == 429 or 500 <= code < 600)
        return False

    def _create_async_client(self) -> Any:
        return self._genai.Client(api_key=self.api_key).aio

    def _convert_messages(self, messages: list[Message]) -> tuple[str | None, list[dict]]:
        """Convert Message objects to Interactions API format."""
        system_prompt = None
        api_messages = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_prompt = msg.content
            else:
                api_messages.append({
                    "type": ROLE_MAP[msg.role],
                    "content": [{"type": "text", "text": msg.content}],
                })

        return system_prompt, api_messages

    async def _generate(self, messages: list[Message]) -> T:
        system_prompt, api_messages = self._convert_messages(messages)

        kwargs = {"model": self.model, "input": api_messages, "store": False, **self.model_args}
        if system_prompt:
            kwargs["system_instruction"] = system_prompt

        interaction = await self._async_client.interactions.create(**kwargs)
        return self._extract(interaction)

    def _extract(self, interaction: Any) -> T:
        return interaction.output_text


class TextClient(GeminiClient[str]): ...


class WebClient(GeminiClient[str]):
    def __init__(self, api_key: str, model: str, **model_args):
        model_args["tools"] = [{"type": "google_search"}]
        super().__init__(api_key, model, **model_args)


class ImageClient(GeminiClient[bytes]):
    async def _generate(self, messages: list[Message]) -> bytes:
        # image generation is one-shot: use the latest prompt, not the conversation
        system_prompt, api_messages = self._convert_messages(messages)
        prompt = api_messages[-1]["content"][0]["text"]

        kwargs = {"model": self.model, "input": prompt, "store": False, **self.model_args}
        if system_prompt:
            kwargs["system_instruction"] = system_prompt

        interaction = await self._async_client.interactions.create(**kwargs)
        return base64.b64decode(interaction.output_image.data)
