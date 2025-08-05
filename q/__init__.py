"""
Q - An LLM-powered programming copilot from the comfort of your command line.

This package provides both a command-line interface and a library API for
interacting with Large Language Models in a programming context.

Library Usage:
    from q import TextGenerator, ImageGenerator
    
    # Text generation
    generator = TextGenerator()
    response = generator.generate("Explain Python decorators", command_type="explain")
    
    # Image generation
    img_gen = ImageGenerator()
    image_path = img_gen.generate_and_save("A serene mountain landscape")

CLI Usage:
    q "what is python"              # Default conversation
    q -e "how does git rebase work" # Explain command
    q -c "sort a list in python"    # Code generation
    q -s "find large files"         # Shell command
    q -i "mountain landscape"       # Image generation
"""

from .generators.text import TextGenerator
from .generators.image import ImageGenerator
from .providers.factory import get_provider
from .config.manager import ConfigManager
from .cli import main

__version__ = "2.0.0"
__api_version__ = "1.0"

__all__ = [
    "TextGenerator",
    "ImageGenerator", 
    "get_provider",
    "ConfigManager",
    "main",
    "__version__",
    "__api_version__"
]