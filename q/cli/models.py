from enum import Enum

from .terminal import InputError


class Tier(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"


MODEL_CONFIGS = {
    "openai": {
        "TextClient": {
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
        "ImageClient": {
            Tier.LOW: {
                "model": "gpt-5.4-nano",
                "tools": [{"type": "image_generation", "quality": "low"}],
            },
            Tier.MED: {
                "model": "gpt-5.4-nano",
                "tools": [{"type": "image_generation", "quality": "medium"}],
            },
            Tier.HIGH: {
                "model": "gpt-5.4-nano",
                "tools": [{"type": "image_generation", "quality": "high"}],
            },
        },
    },
    "anthropic": {
        "TextClient": {
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
        },
    },
    "google": {
        "TextClient": {
            Tier.LOW: {
                "model": "gemini-3.1-flash-lite",
            },
            Tier.MED: {
                "model": "gemini-3.5-flash",
                "generation_config": {"thinking_level": "low"},
            },
            Tier.HIGH: {
                "model": "gemini-3.5-flash",
                "generation_config": {"thinking_level": "high"},
            },
        },
        "ImageClient": {
            Tier.LOW: {
                "model": "gemini-2.5-flash-image",
            },
            Tier.MED: {
                "model": "gemini-3.1-flash-image",
            },
            Tier.HIGH: {
                "model": "gemini-3-pro-image",
            },
        },
    },
}

MODEL_CONFIGS["openai"]["WebClient"] = MODEL_CONFIGS["openai"]["TextClient"]
MODEL_CONFIGS["google"]["WebClient"] = MODEL_CONFIGS["google"]["TextClient"]


def lookup(provider: str, client_name: str, tier: Tier) -> tuple[str, dict]:
    """Return (model_name, model_args) for a given provider, client, and tier."""
    if provider not in MODEL_CONFIGS:
        raise InputError(f"unknown provider: {provider}")
    if client_name not in MODEL_CONFIGS[provider]:
        raise InputError(f"{provider} does not support {client_name}")

    config = MODEL_CONFIGS[provider][client_name][tier]
    model = config["model"]
    model_args = {k: v for k, v in config.items() if k != "model"}
    return model, model_args
