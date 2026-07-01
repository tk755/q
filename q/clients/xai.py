from typing import Any

from .openai import OpenAIClient
from .openai import WebClient as OpenAIWebClient

__all__ = ["TextClient", "WebClient"]


class XAIClient[T](OpenAIClient[T]):
    """Base client for xAI via the OpenAI Responses API."""

    SPOOF_ASSISTANT_IMAGES = False

    @staticmethod
    def _create_async_client(api_key: str) -> Any:
        import openai
        return openai.AsyncOpenAI(api_key=api_key, base_url="https://api.x.ai/v1")


class TextClient(XAIClient[str]): ...


class WebClient(XAIClient[str], OpenAIWebClient): ...
