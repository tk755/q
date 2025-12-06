import json
import os
import toml
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values, set_key

from .terminal import prompt


RESOURCES_DIR = Path.home() / '.q'
ENV_PATH = RESOURCES_DIR / '.env'
CONFIG_PATH = RESOURCES_DIR / 'config.toml'
SESSIONS_DIR = RESOURCES_DIR / 'sessions'

API_KEY_SUFFIX = '_API_KEY'


# region Data Classes

@dataclass
class Config:
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    language: str = "python"
    current_session_id: int = 1


@dataclass
class Session:
    id: int
    messages: list[dict] = field(default_factory=list)
    created: str = ""
    updated: str = ""


@dataclass
class State:
    secrets: dict[str, str]
    config: Config
    session: Session


# region Secrets

def _env_key(provider: str) -> str:
    return f"{provider.upper()}{API_KEY_SUFFIX}"


def _load_secrets() -> dict[str, str]:
    """Load secrets from env vars and ~/.q/.env file."""
    file_secrets = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    secrets = {}
    for key, value in file_secrets.items():
        if key.endswith(API_KEY_SUFFIX) and value:
            provider = key[:-len(API_KEY_SUFFIX)].lower()
            secrets[provider] = os.environ.get(key) or value
    return secrets


def save_secret(key: str, value: str) -> None:
    """Append secret to ~/.q/.env with 0600 permissions."""
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    if not ENV_PATH.exists():
        ENV_PATH.touch(mode=0o600)
    set_key(ENV_PATH, key, value)


def get_api_key(state: State, provider: str) -> str:
    """Get API key for provider, prompting if missing."""
    if not state.secrets.get(provider):
        key = prompt(f"{provider} API key not found. Please paste your key: ", color='yellow').strip()
        save_secret(_env_key(provider), key)
        state.secrets[provider] = key
        return key
    return state.secrets[provider]


# region Config

def _load_config() -> Config:
    """Load config from TOML or create defaults."""
    if not CONFIG_PATH.exists():
        config = Config()
        _save_config(config)
        return config

    data = toml.load(CONFIG_PATH)
    defaults = data.get('defaults', {})
    session = data.get('session', {})

    return Config(
        provider=defaults.get('provider', 'openai'),
        model=defaults.get('model', 'gpt-4.1-mini'),
        language=defaults.get('language', 'python'),
        current_session_id=session.get('current', 1)
    )


def _save_config(config: Config) -> None:
    """Save config to TOML."""
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        'defaults': {
            'provider': config.provider,
            'model': config.model,
            'language': config.language,
        },
        'session': {
            'current': config.current_session_id,
        },
    }
    with open(CONFIG_PATH, 'w') as f:
        toml.dump(data, f)


# region Session

def load_session(session_id: int) -> Session | None:
    """Load session by ID. Returns None if not found."""
    path = SESSIONS_DIR / f'{session_id}.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Session(
        id=data['id'],
        messages=data.get('messages', []),
        created=data.get('created', ''),
        updated=data.get('updated', '')
    )


def _save_session(session: Session) -> None:
    """Save session to JSON file."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session.updated = datetime.now(timezone.utc).isoformat()
    path = SESSIONS_DIR / f'{session.id}.json'
    data = {
        'id': session.id,
        'messages': session.messages,
        'created': session.created,
        'updated': session.updated
    }
    path.write_text(json.dumps(data, indent=2))


def create_session() -> Session:
    """Create new session with next available ID."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    existing = [int(p.stem) for p in SESSIONS_DIR.glob('*.json') if p.stem.isdigit()]
    next_id = max(existing, default=0) + 1
    now = datetime.now(timezone.utc).isoformat()
    return Session(id=next_id, messages=[], created=now, updated=now)


def get_sessions() -> list[Session]:
    """Return all sessions sorted by ID."""
    if not SESSIONS_DIR.exists():
        return []

    sessions = []
    for path in sorted(SESSIONS_DIR.glob('*.json'), key=lambda p: int(p.stem)):
        try:
            data = json.loads(path.read_text())
            sessions.append(Session(
                id=data['id'],
                messages=data.get('messages', []),
                created=data.get('created', ''),
                updated=data.get('updated', '')
            ))
        except (json.JSONDecodeError, KeyError):
            continue
    return sessions


# region State

def load_state() -> State:
    """Load secrets, config, and current session from ~/.q/"""
    secrets = _load_secrets()
    config = _load_config()
    session = load_session(config.current_session_id) or create_session()
    return State(secrets, config, session)


def save_state(state: State) -> None:
    """Persist config and current session to ~/.q/"""
    state.config.current_session_id = state.session.id
    _save_config(state.config)
    _save_session(state.session)
