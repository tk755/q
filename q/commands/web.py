"""
Web search command implementation.

Handles the -w/--web command for searching the internet.
"""

from typing import List
from .base import BaseCommand
from ..config.models import Message, MessageRole, ModelParameters


class WebCommand(BaseCommand):
    """
    Command for web search functionality.
    
    Maintains exact behavior from original q.py web command with
    web search tools configuration.
    """
    
    @property
    def flags(self) -> List[str]:
        """Command flags."""
        return ['-w', '--web']
    
    @property
    def description(self) -> str:
        """Description for help text."""
        return "search the internet (expensive)"
    
    def get_messages(self, text: str) -> List[Message]:
        """
        Get messages for web search.
        
        Uses the exact system prompt from original q.py to maintain
        consistent web search behavior focused on data retrieval.
        
        Args:
            text: Search query or information request
            
        Returns:
            List of messages for web search request
        """
        return [
            Message(
                role=MessageRole.DEVELOPER,
                content=(
                    "You fetch real-time data from the internet. Always respond with only the data requested. "
                    "Do not provide additional information in the form of context, background, or links. "
                    "The response should be less than a single sentence."
                )
            ),
            Message(
                role=MessageRole.USER,
                content=f"Fetch the following information: {text}."
            )
        ]
    
    def get_model_params(self) -> ModelParameters:
        """
        Get model parameters for web search.
        
        Uses mini model with web search tools configured
        exactly as in original q.py.
        
        Returns:
            Model parameters with web search tools
        """
        return ModelParameters(
            model='gpt-4.1-mini',
            max_output_tokens=1024,
            temperature=0.0,
            tools=[{
                'type': 'web_search_preview',
                'search_context_size': 'low'
            }]
        )