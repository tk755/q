"""
Response processing utilities for text formatting and cleanup.

Extracted from the original q.py script to maintain exact same processing
behavior while making it reusable across the modular system.
"""

import re
from termcolor import colored
from typing import Any, Dict


class ResponseProcessor:
    """Handles processing and formatting of LLM responses."""
    
    @staticmethod
    def process_text_response(text_response: str) -> str:
        """
        Process text response with formatting and cleanup.
        
        This preserves the exact processing logic from the original q.py:
        - Remove markdown formatting from code responses
        - Shorten links from web search responses
        - Convert bash code blocks into colored text with $ prefix
        - Convert non-bash code blocks into colored text
        - Convert inline-code into colored text
        - Convert two-plus newlines into only two
        
        Args:
            text_response: Raw text response from LLM
            
        Returns:
            Processed and formatted text response
        """
        # remove markdown formatting from code responses
        text_response = re.sub(r'^```.*?\n(.*)\n```$', r'\1', text_response, flags=re.DOTALL)

        # shorten links from web search responses
        text_response = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text_response).strip()

        # convert bash code blocks into colored text with $ prefix
        text_response = re.sub(
            r'```bash\n?(.*?)```', 
            lambda m: colored('\n'.join('$ ' + line for line in m.group(1).strip().split('\n')), 'cyan'), 
            text_response, 
            flags=re.DOTALL
        )
        
        # convert non-bash code blocks into colored text
        text_response = re.sub(
            r'```(?:\w+\n?)?(.*?)```', 
            lambda m: colored(m.group(1).strip(), 'cyan'), 
            text_response, 
            flags=re.DOTALL
        )
        
        # convert inline-code into colored text
        text_response = re.sub(r'`([^`]+)`', lambda m: colored(m.group(1), 'cyan'), text_response)

        # convert two-plus newlines into only two
        text_response = re.sub(r'\n{2,}', '\n\n', text_response)

        return text_response
    
    @staticmethod
    def format_for_cli(response: str, verbose: bool = False, model_args: Dict[str, Any] = None, messages: list = None) -> str:
        """
        Format response for CLI display with optional verbose information.
        
        Args:
            response: Processed response text
            verbose: Whether to include verbose debugging information
            model_args: Model parameters for verbose output
            messages: Message history for verbose output
            
        Returns:
            Formatted response ready for CLI display
        """
        if not verbose:
            return response
            
        # Format verbose output similar to original q.py
        verbose_output = []
        
        if model_args:
            verbose_output.append(colored('MODEL PARAMETERS:', 'red'))
            for arg, value in model_args.items():
                verbose_output.append(f"{colored(f'{arg}:', 'green')} {value}")
        
        if messages:
            verbose_output.append(colored('\nMESSAGES:', 'red'))
            for message in messages:
                if isinstance(message, dict):
                    if message.get('role'):
                        verbose_output.append(f"{colored(f'{message['role'].capitalize()}:', 'green')} {message['content']}")
                    elif message.get('type'):
                        verbose_output.append(f"{colored(f'{message['type']}:', 'green')} {message['id']}")
        
        if verbose_output:
            return '\n'.join(verbose_output) + '\n\n' + response
        
        return response