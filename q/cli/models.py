from enum import Enum

from .terminal import InputError


class Tier(Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"

MAX_TOKENS = 16384

MODEL_CONFIGS = {
    "openai": {
        "TextClient": {
            Tier.LOW: {
                "model": "gpt-5.4-mini",
                "reasoning": {"effort": "none"},
                "max_output_tokens": MAX_TOKENS,
            },
            Tier.MED: {
                "model": "gpt-5.4",
                "reasoning": {"effort": "none"},
                "max_output_tokens": MAX_TOKENS,
            },
            Tier.HIGH: {
                "model": "gpt-5.4",
                "reasoning": {"effort": "high"},
                "max_output_tokens": MAX_TOKENS*2,
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
                "max_tokens": MAX_TOKENS,
            },
            Tier.MED: {
                "model": "claude-sonnet-5",
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": "medium"},
                "max_tokens": MAX_TOKENS,
            },
            Tier.HIGH: {
                "model": "claude-opus-4-8",
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": "high"},
                "max_tokens": MAX_TOKENS,
            },
        },
    },
    "google": {
        "TextClient": {
            Tier.LOW: {
                "model": "gemini-3.1-flash-lite",
                "generation_config": {"thinking_level": "low", "max_output_tokens": MAX_TOKENS},
            },
            Tier.MED: {
                "model": "gemini-3.5-flash",
                "generation_config": {"thinking_level": "low", "max_output_tokens": MAX_TOKENS},
            },
            Tier.HIGH: {
                "model": "gemini-3.1-pro-preview",
                "generation_config": {"thinking_level": "low", "max_output_tokens": MAX_TOKENS},
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
    "xai": {
        "TextClient": {
            Tier.LOW: {
                "model": "grok-4.3",
                "reasoning": {"effort": "none"},
                "max_output_tokens": MAX_TOKENS,
            },
            Tier.MED: {
                "model": "grok-4.3",
                "reasoning": {"effort": "low"},
                "max_output_tokens": MAX_TOKENS,
            },
            Tier.HIGH: {
                "model": "grok-4.3",
                "reasoning": {"effort": "medium"},
                "max_output_tokens": MAX_TOKENS,
            },
        },
    },
}

MODEL_CONFIGS["openai"]["WebClient"] = MODEL_CONFIGS["openai"]["TextClient"]
MODEL_CONFIGS["anthropic"]["WebClient"] = MODEL_CONFIGS["anthropic"]["TextClient"]
MODEL_CONFIGS["google"]["WebClient"] = MODEL_CONFIGS["google"]["TextClient"]
MODEL_CONFIGS["xai"]["WebClient"] = MODEL_CONFIGS["xai"]["TextClient"]


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
