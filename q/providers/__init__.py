import importlib
from types import ModuleType

from q.client import Client


def load_provider_module(provider_str: str) -> ModuleType:
    """Dynamically load provider module."""
    try:
        return importlib.import_module(f"q.providers.{provider_str}")
    except ModuleNotFoundError as err:
        raise ImportError(f"unknown provider: {provider_str}") from err


def load_client_class(provider_str: str, client_str: str) -> type[Client]:
    """Dynamically load provider client class."""
    provider_module = load_provider_module(provider_str)
    client_class = getattr(provider_module, client_str, None)
    if client_class is None:
        raise ImportError(f"{provider_str} does not support {client_str}")
    return client_class
