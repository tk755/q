import asyncio
from .client import BaseClient, Messages


class ConversationAgent:
    """Conversational agent with persistent message history and stateful dialogue."""
    
    def __init__(self, client: BaseClient, system_prompt: str | None = None):
        """Initialize conversation agent with LLM client and optional system prompt."""
        self.client = client
        self.messages: Messages = []
        
        if system_prompt:
            self.add_system_message(system_prompt)
    
    def prompt(self, message: str, model: str, **kwargs) -> str:
        """Process user message and return response while updating message history."""
        # Add user message to history
        self.add_user_message(message)
        
        # Get current conversation history
        messages = self.get_messages()
        
        # Generate response using client
        response = self.client.prompt(messages, model, **kwargs)
        
        # Add response to history
        self.add_assistant_message(response)
        
        return response
    
    async def prompt_async(self, message: str, model: str, **kwargs) -> str:
        """Async process user message and return response while updating message history."""
        # Add user message to history
        self.add_user_message(message)
        
        # Get current conversation history
        messages = self.get_messages()
        
        # Generate response using client
        response = await self.client.prompt_async(messages, model, **kwargs)
        
        # Add response to history
        self.add_assistant_message(response)
        
        return response
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.messages.append({"role": role, "content": content})
    
    def add_system_message(self, content: str) -> None:
        """Add system message to history."""
        self.add_message("system", content)
    
    def add_user_message(self, content: str) -> None:
        """Add user message to history."""
        self.add_message("user", content)
    
    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to history."""
        self.add_message("assistant", content)
    
    def get_messages(self) -> Messages:
        """Get copy of conversation history."""
        return self.messages.copy()
    
    def clear_messages(self) -> None:
        """Clear all conversation history."""
        self.messages.clear()
    
    def drop_messages(self, n: int = 1) -> None:
        """Drop the last N messages from history."""
        if n > 0 and self.messages:
            self.messages = self.messages[:-n]
    
    def drop_exchanges(self, n: int = 1) -> None:
        """Drop the last N conversation exchanges (user message + responses)."""
        if n <= 0:
            return
        
        user_messages_found = 0
        # Go backwards through history to find the Nth user message from the end
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].get('role') == 'user':
                user_messages_found += 1
                if user_messages_found == n:
                    # Drop everything from this point to the end
                    self.messages = self.messages[:i]
                    return


class BatchAgent:
    """Agent for processing multiple messages concurrently."""
    
    def __init__(self, client: BaseClient):
        """Initialize batch agent with LLM client."""
        self.client = client
    
    async def batch_prompt(self, messages: list[str], model: str, n_threads: int = 16, **kwargs) -> list[str]:
        """Process multiple messages concurrently and return responses in order."""
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(n_threads)
        
        async def process_message(message: str) -> str:
            async with semaphore:
                return await self.client.prompt_async([{"role": "user", "content": message}], model, **kwargs)
        
        # Process all messages concurrently
        tasks = [process_message(message) for message in messages]
        responses = await asyncio.gather(*tasks)
        
        return responses
