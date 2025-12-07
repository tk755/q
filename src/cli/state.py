import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values, set_key
from pydantic import BaseModel, Field

from .terminal import prompt
from ..message import Message


RESOURCES_DIR = Path.home() / '.q'
ENV_PATH = RESOURCES_DIR / '.env'
CONFIG_PATH = RESOURCES_DIR / 'config.json'
SESSIONS_DIR = RESOURCES_DIR / 'sessions'


class Config(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    code_lang: str = "python"
    current_session_id: int = 1


class Session(BaseModel):
    id: int
    messages: list[Message] = Field(default_factory=list)
    created: datetime | None = None
    updated: datetime | None = None


class StateManager:
    """Manages application state: secrets, config, and current session."""

    def __init__(self):
        # ensure directories exist
        RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        # load state
        self._load_secrets()
        self._load_config()
        if not self.load_session(self._config.current_session_id):
            self.new_session()

    def save(self) -> None:
        """Persist config and session to disk."""
        self._config.current_session_id = self._session.id
        self._save_config()
        self._save_session()

    # region Properties

    @property
    def provider(self) -> str:
        return self._config.provider

    @property
    def model(self) -> str:
        return self._config.model

    @property
    def code_lang(self) -> str:
        return self._config.code_lang

    @property
    def session_id(self) -> int:
        return self._session.id

    @property
    def messages(self) -> list[Message]:
        return self._session.messages

    @messages.setter
    def messages(self, value: list[Message]) -> None:
        self._session.messages = value

    # region Secrets

    def get_api_key(self, provider: str) -> str:
        """Get API key for provider, prompting if not found."""
        provider = provider.lower()
        if provider not in self._secrets:
            key = prompt(f"{provider} API key not found. Please paste your key: ", color='yellow').strip()
            self._save_secret(provider, key)
            self._secrets[provider] = key
        return self._secrets[provider]

    def _load_secrets(self) -> None:
        """Load secrets from ~/.q/.env. Format: provider=key."""
        self._secrets = {}
        if not ENV_PATH.exists():
            return
        for provider, key in dotenv_values(ENV_PATH).items():
            if key:
                self._secrets[provider.lower()] = os.environ.get(provider) or key

    def _save_secret(self, provider: str, key: str) -> None:
        """Save secret to ~/.q/.env."""
        if not ENV_PATH.exists():
            ENV_PATH.touch(mode=0o600)
        set_key(ENV_PATH, provider.lower(), key)

    # region Config

    def _load_config(self) -> None:
        """Load config from JSON file."""
        if not CONFIG_PATH.exists():
            self._config = Config()
            return
        self._config = Config.model_validate_json(CONFIG_PATH.read_text())

    def _save_config(self) -> None:
        """Save config to JSON file."""
        CONFIG_PATH.write_text(self._config.model_dump_json(indent=2))

    # region Session

    def new_session(self) -> None:
        """Create and switch to a new session."""
        existing = [int(p.stem) for p in SESSIONS_DIR.glob('*.json') if p.stem.isdigit()]
        now = datetime.now(timezone.utc)
        self._session = Session(
            id=max(existing, default=0) + 1,
            messages=[],
            created=now,
            updated=now
        )

    def list_sessions(self) -> list[Session]:
        """Return all sessions sorted by ID."""
        sessions = []
        for path in sorted(SESSIONS_DIR.glob('*.json'), key=lambda p: int(p.stem)):
            try:
                sessions.append(Session.model_validate_json(path.read_text()))
            except ValueError:
                continue
        return sessions

    def load_session(self, session_id: int) -> bool:
        """Load session by ID. Returns False if not found."""
        path = SESSIONS_DIR / f'{session_id}.json'
        if not path.exists():
            return False
        self._session = Session.model_validate_json(path.read_text())
        return True

    def _save_session(self) -> None:
        """Save current session to JSON."""
        self._session.updated = datetime.now(timezone.utc)
        path = SESSIONS_DIR / f'{self._session.id}.json'
        path.write_text(self._session.model_dump_json(indent=2))
