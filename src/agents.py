import asyncio
from typing import Generic, TypeVar

from .client import Client
from .message import Message, Role


T = TypeVar('T')


class ChatAgent(Generic[T]):
    """Conversational agent with persistent message history."""

    def __init__(self, client: Client[T], system: str | None = None, messages: list[Message] | None = None):
        self.client = client
        self.messages: list[Message] = messages.copy() if messages else []

        if system:
            self.messages.append(Message(role=Role.SYSTEM, content=system))

    async def prompt(self, text: str) -> T:
        """Generate response and update conversation history."""
        self.messages.append(Message(role=Role.USER, content=text))
        response = await self.client.generate(self.messages)

        # only add to history if response is a string
        if isinstance(response, str):
            self.messages.append(Message(role=Role.ASSISTANT, content=response))

        return response

    def drop_exchanges(self, n: int = 1) -> None:
        """Drop the last N conversation exchanges (user message + responses)."""
        if n <= 0:
            return

        user_messages_found = 0
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].role == Role.USER:
                user_messages_found += 1
                if user_messages_found == n:
                    self.messages = self.messages[:i]
                    return


class BatchAgent(Generic[T]):
    """Batch agent for applying a single prompt to multiple inputs concurrently."""

    def __init__(self, client: Client[T], system: str | None = None):
        self.client = client
        self.system = system

    async def batch_prompt(self, text_list: list[str], n_threads: int = 8) -> list[T]:
        """Process multiple inputs concurrently and return the outputs in order."""
        semaphore = asyncio.Semaphore(n_threads)

        async def process(text: str) -> T:
            async with semaphore:
                messages: list[Message] = []
                if self.system:
                    messages.append(Message(role=Role.SYSTEM, content=self.system))
                messages.append(Message(role=Role.USER, content=text))
                return await self.client.generate(messages)

        tasks = [process(text) for text in text_list]
        return await asyncio.gather(*tasks)
