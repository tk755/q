from ..agents import ChatAgent
from ..clients import ImageClient, WebClient


class QAgent(ChatAgent):

    def web_prompt(self, prompt: str) -> str:
        if not isinstance(self.client, WebClient):
            raise ValueError(f"Web search not supported by {self.client}")

        self.add_user_message(prompt)
        response = self.client.web_search(self.get_messages(), self.model, **self.model_args)
        self.add_assistant_message(response)
        return response

    def image_prompt(self, prompt: str, model: str | None = None) -> bytes:
        if not isinstance(self.client, ImageClient):
            raise ValueError(f"Image generation not supported by {self.client}")

        self.add_user_message(prompt)
        image_bytes = self.client.generate_image(
            self.get_messages(),
            model or self.model,
            **self.model_args
        )
        self.add_assistant_message("[Generated image]")
        return image_bytes
