from enum import Enum


class QError(Exception):
    """CLI error."""


class Tier(Enum):
    MINI = "mini"
    FULL = "full"
    DEEP = "deep"


MODELS = {
    "openai": {
        Tier.MINI: {"model": "gpt-5-nano", "reasoning": {"effort": "low"}, "text": {"verbosity": "low"}},
        Tier.FULL: {"model": "gpt-5-mini", "reasoning": {"effort": "medium"}, "text": {"verbosity": "low"}},
        Tier.DEEP: {"model": "gpt-5.1", "reasoning": {"effort": "high"}},
    },
    "anthropic": {
        Tier.MINI: {"model": "claude-haiku-4-5"},
        Tier.FULL: {"model": "claude-sonnet-4-5"},
        Tier.DEEP: {"model": "claude-opus-4-5"},
    },
}


def _lookup(provider: str, tier: Tier) -> tuple[str, str, dict]:
    if provider not in MODELS:
        raise QError(f"unknown provider: {provider}")
    
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
        try:
            # provider:tier (e.g. "openai:deep")
            return _lookup(provider, Tier(value))
        except ValueError:
            # provider:model (e.g. "openai:gpt-5-pro")
            return provider, value, {}

    # tier (e.g. "deep")
    try:
        return _lookup(default_provider, Tier(arg))
    except ValueError:
        pass

    # provider (e.g. "openai")
    if arg in MODELS:
        return _lookup(arg, default_tier)

    raise QError(f"invalid model: {arg}")
