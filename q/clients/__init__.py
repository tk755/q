import importlib
from types import ModuleType

from .base import Client


def load_provider_module(provider_name: str) -> ModuleType:
    """Dynamically load provider module."""
    try:
        return importlib.import_module(f"q.clients.{provider_name}")
    except ModuleNotFoundError as err:
        raise ImportError(f"unknown provider: {provider_name}") from err


def load_client_class(provider_name: str, client_name: str) -> type[Client]:
    """Dynamically load provider client class."""
    provider_module = load_provider_module(provider_name)
    client_class = getattr(provider_module, client_name, None)
    if client_class is None:
        raise ImportError(f"{provider_name} does not support {client_name}")
    return client_class
