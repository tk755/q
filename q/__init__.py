import sys

from .clients import anthropic, google, openai
from .core import Client, Message, Role

__version__ = "2.0.0.dev10"

__all__ = ["Client", "Message", "Role"]

# expose provider modules at the package root so `from q.openai import TextClient` works
sys.modules["q.openai"] = openai
sys.modules["q.anthropic"] = anthropic
sys.modules["q.google"] = google
