import base64
from typing import Any
from ..client import *


class OpenAIClient(TextClient, ImageClient, WebClient):
    """OpenAI API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        super().__init__()

    def _import_sdk(self):
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI client requires 'openai' package.")
        self._openai = openai

    def _validate_auth(self):
        try:
            test_client = self._openai.OpenAI(api_key=self.api_key)
            # Make a minimal request to validate the key
            test_client.models.list()
        except Exception as e:
            raise ValueError(f"OpenAI API key validation failed: {e}")

    def _create_async_client(self) -> Any:
        return self._openai.AsyncOpenAI(api_key=self.api_key)

    def _should_retry(self, error: Exception) -> bool:
        # Retryable errors: rate limits, connection issues, server errors
        if isinstance(error, (
            self._openai.RateLimitError,
            self._openai.APIConnectionError,
            self._openai.APITimeoutError,
            self._openai.InternalServerError
        )):
            return True

        # Generic API errors with retryable status codes
        if isinstance(error, self._openai.APIStatusError):
            if error.status_code == 429 or 500 <= error.status_code < 600:
                return True

        return False
    
    # region Text Client

    async def _generate_text_async(self, messages: Messages, model: str, **model_args) -> Any:
        return await self._async_client.responses.create(
            input=messages,
            model=model,
            **model_args
        )

    def _extract_text(self, response: Any) -> str:
        return response.output_text
    
    # region Image Client

    async def _generate_image_async(self, messages: Messages, model: str, **model_args) -> Any:
        # Add image generation tool
        if 'tools' not in model_args:
            model_args['tools'] = [{
                'type': 'image_generation',
                'size': '1024x1024',
                'quality': 'auto'  # auto, low, medium, high
            }]

        return await self._async_client.responses.create(
            input=messages,
            model=model,
            **model_args
        )

    async def _edit_image_async(self, messages: Messages, model: str, **model_args) -> Any:
        raise NotImplementedError("Image editing not yet implemented")

    def _extract_image(self, response: Any) -> bytes:
        for output in response.output:
            if output.type == 'image_generation_call':
                return base64.b64decode(output.result)

        # If no image found, raise an error
        raise ValueError("No image_generation_call found in response output")

    # region Web Client

    async def _web_search_async(self, messages: Messages, model: str, **model_args) -> Any:
        # Add web search tool
        if 'tools' not in model_args:
            model_args['tools'] = [{
                'type': 'web_search_preview',
                'search_context_size': 'low'  # low, medium, high
            }]

        return await self._async_client.responses.create(
            input=messages,
            model=model,
            **model_args
        )

    def _extract_search_results(self, response: Any) -> str:
        return response.output_text
    