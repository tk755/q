import contextlib
from enum import Enum

from q.client import Client
from q.providers import load_client_class

from .terminal import InputError


class Tier(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"


MODEL_CONFIGS = {
    "openai": {
        'TextClient': {
            Tier.LOW: {
                "model": "gpt-5.4-nano",
                "reasoning": {"effort": "low"},
            },
            Tier.MED: {
                "model": "gpt-5.4-mini",
                "reasoning": {"effort": "medium"},
            },
            Tier.HIGH: {
                "model": "gpt-5.4",
                "reasoning": {"effort": "high"},
            },
        },
    },
    "anthropic": {
        'TextClient': {
            Tier.LOW: {
                "model": "claude-haiku-4-5",
                "max_tokens": 2000,
            },
            Tier.MED: {
                "model": "claude-sonnet-4-6",
                "max_tokens": 4000,
            },
            Tier.HIGH: {
                "model": "claude-opus-4-8",
                "max_tokens": 16000,
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": "high"},
            },
        }
    },
    "google": {
        'TextClient': {
            Tier.LOW: {
                "model": "gemini-3.1-flash-lite",
            },
            Tier.MED: {
                "model": "gemini-3-flash-preview",
                "generation_config": {"thinking_level": "medium"},
            },
            Tier.HIGH: {
                "model": "gemini-3.5-flash",
                "generation_config": {"thinking_level": "high"},
            },
        },
    }
}

MODEL_CONFIGS['openai']['WebClient'] = MODEL_CONFIGS['openai']['TextClient']
MODEL_CONFIGS['openai']['ImageClient'] = MODEL_CONFIGS['openai']['TextClient']

MODEL_CONFIGS['google']['WebClient'] = MODEL_CONFIGS['google']['TextClient']
MODEL_CONFIGS['google']['ImageClient'] = {
    Tier.LOW: {"model": "gemini-2.5-flash-image"},
    Tier.MED: {"model": "gemini-3.1-flash-image"},
    Tier.HIGH: {"model": "gemini-3-pro-image"},
}


def _lookup(provider: str, client_name: str, tier: Tier) -> tuple[str, str, dict]:
    if provider not in MODEL_CONFIGS:
        raise InputError(f"unknown provider: {provider}")
    if client_name not in MODEL_CONFIGS[provider]:
        raise InputError(f"{provider} does not support {client_name}")

    config = MODEL_CONFIGS[provider][client_name][tier]
    model = config["model"]
    model_args = {k: v for k, v in config.items() if k != "model"}
    return provider, model, model_args


def _resolve_model_config(value: str | None, tier: Tier, default_provider: str, client_name: str) -> tuple[str, str, dict]:
    """Resolve a model flag value to (provider, model_name, model_args)."""
    if value is None:
        return _lookup(default_provider, client_name, tier)
    value = value.lower()

    # provider:tier or provider:model
    if ":" in value:
        provider, rest = value.split(":", 1)
        with contextlib.suppress(ValueError):
            # provider:tier (e.g. "openai:high")
            return _lookup(provider, client_name, Tier(rest))
        # provider:model (e.g. "openai:gpt-4.1-nano")
        return provider, rest, {}

    # tier (e.g. "high")
    with contextlib.suppress(ValueError):
        return _lookup(default_provider, client_name, Tier(value))

    # provider (e.g. "openai")
    if value in MODEL_CONFIGS:
        return _lookup(value, client_name, tier)

    raise InputError(f"invalid model: {value}")


def resolve_client(value: str | None, tier: Tier, default_provider: str, client_name: str) -> tuple[str, type[Client], str, dict]:
    """Resolve a model flag to (provider, client_class, model_name, model_args)."""
    provider, model, model_args = _resolve_model_config(value, tier, default_provider, client_name)
    client_class = load_client_class(provider, client_name)
    return provider, client_class, model, model_args
