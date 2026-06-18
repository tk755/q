import contextlib
from enum import Enum

from .terminal import UserError


class Tier(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"
    MAX = "max"


MODELS = {
    "openai": {
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
        Tier.MAX: {
            "model": "gpt-5.5",
            "reasoning": {"effort": "xhigh"},
        },
    },
    "anthropic": {
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
        Tier.MAX: {
            "model": "claude-opus-4-8",
            "max_tokens": 20000,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "xhigh"},
        },
    },
}


def _lookup(provider: str, tier: Tier) -> tuple[str, str, dict]:
    if provider not in MODELS:
        raise UserError(f"unknown provider: {provider}")

    config = MODELS[provider][tier]
    model = config["model"]
    model_args = {k: v for k, v in config.items() if k != "model"}
    return provider, model, model_args


def resolve_model_arg(arg: str | None, default_tier: Tier, default_provider: str) -> tuple[str, str, dict]:
    """Return (provider, model_name, model_args)."""
    if arg is None:
        return _lookup(default_provider, default_tier)

    # provider:value
    if ":" in arg:
        provider, value = arg.split(":", 1)
        with contextlib.suppress(ValueError):
            # provider:tier (e.g. "openai:high")
            return _lookup(provider, Tier(value))
        # provider:model (e.g. "openai:gpt-4.1-nano")
        return provider, value, {}

    # tier (e.g. "high")
    with contextlib.suppress(ValueError):
        return _lookup(default_provider, Tier(arg))

    # provider (e.g. "openai")
    if arg in MODELS:
        return _lookup(arg, default_tier)

    raise UserError(f"invalid model: {arg}")
