from .clients import load_client_class
from .clients.base import Client, Message, Role

__all__ = ["Client", "Message", "Role", "load_client_class"]

__version__ = "2.0.0.dev12"

# expose providers as top-level modules
import sys as _sys  # noqa: I001
from .clients import anthropic, google, openai, xai

_sys.modules[f"{__name__}.openai"] = openai
_sys.modules[f"{__name__}.anthropic"] = anthropic
_sys.modules[f"{__name__}.google"] = google
_sys.modules[f"{__name__}.xai"] = xai

del _sys
