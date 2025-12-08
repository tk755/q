import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import humanize
from dotenv import dotenv_values, set_key
from pydantic import BaseModel, Field
from termcolor import colored

from ..message import Message, Role
from .terminal import qinput

RESOURCES_DIR = Path.home() / ".q"
CONFIG_PATH = RESOURCES_DIR / "config.json"
SESSIONS_DIR = RESOURCES_DIR / "sessions"
ENV_PATH = RESOURCES_DIR / ".env"


class Config(BaseModel):
    """Config schema and defaults."""

    model: str = "openai/gpt-4.1-mini"
    code_lang: str = "python"
    current_session_id: int = 1


class Session(BaseModel):
    """Conversation session with message history."""

    id: int
    messages: list[Message] = Field(default_factory=list)
    created: datetime | None = None
    updated: datetime | None = None


class SessionManager:
    """Stateless manager for sessions, config, and secrets."""

    # region Public Interface

    # Config

    @classmethod
    def load_model(cls) -> str:
        """Load model from config."""
        return cls._read_config().model

    @classmethod
    def load_code_lang(cls) -> str:
        """Load code language from config."""
        return cls._read_config().code_lang

    # Secrets

    @classmethod
    def load_api_key(cls, provider: str) -> str:
        """Load API key. Prompts and saves if missing."""
        secrets = cls._read_secrets()
        provider_lower = provider.lower()

        if provider_lower not in secrets:
            key = qinput(f"{provider} API key not found. Enter key: ", secret=True).strip()
            # TODO: add load_provider_module(provider).validate_key(key)
            cls._write_secret(provider_lower, key)
            return key

        return secrets[provider_lower]

    # Messages

    @classmethod
    def load_messages(cls) -> list[Message] | None:
        """Load messages from active session."""
        session = cls._read_session(cls._read_config().current_session_id)
        return session.messages if session else None

    @classmethod
    def save_messages(cls, messages: list[Message]) -> None:
        """Creates or updates active session with messages."""
        session_id = cls._read_config().current_session_id
        session = cls._read_session(session_id)
        now = datetime.now(timezone.utc)

        if session is None:
            session = Session(id=session_id, messages=messages, created=now, updated=now)
        else:
            session.messages = messages
            session.updated = now

        cls._write_session(session)

    # Session management

    @classmethod
    def load_session_id(cls) -> int:
        """Load active session ID."""
        return cls._read_config().current_session_id

    @classmethod
    def format_session_list(cls) -> str:
        """Format all sessions for terminal display."""
        sessions = cls._list_all_sessions()
        if not sessions:
            return "No sessions found."

        current_id = cls._read_config().current_session_id
        term_width = shutil.get_terminal_size().columns

        lines = []
        for s in sessions:
            age = humanize.naturaltime(s.updated) if s.updated else "unknown"
            prefix_len = len(f"    {s.id}.  ")
            suffix_len = len(f" ({age})")
            max_len = max(20, term_width - prefix_len - suffix_len - 5)

            preview = "(empty)"
            for msg in reversed(s.messages):
                if msg.role == Role.USER:
                    preview = msg.content[:max_len] + "..." if len(msg.content) > max_len else msg.content
                    break

            line = f"    {s.id}.  {preview} ({age})"
            if s.id != current_id:
                line = colored(line, "dark_grey")
            lines.append(line)

        return "\n".join(lines)

    @classmethod
    def switch_session(cls, session_id: int) -> bool:
        """Switch active session. Returns False if not found."""
        if cls._read_session(session_id) is None:
            return False
        cls._save_active_session_id(session_id)
        return True

    @classmethod
    def new_session(cls) -> None:
        """Create new session ID. Session file created on save_messages()."""
        cls._ensure_dirs()
        existing = [int(p.stem) for p in SESSIONS_DIR.glob("*.json") if p.stem.isdigit()]
        cls._save_active_session_id(max(existing, default=0) + 1)

    # region Private Helpers

    @classmethod
    def _ensure_dirs(cls) -> None:
        """Create resource directories if needed."""
        RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _read_config(cls) -> Config:
        """Read config, merging file overrides with defaults."""
        if not CONFIG_PATH.exists():
            return Config()
        try:
            return Config.model_validate_json(CONFIG_PATH.read_text())
        except Exception:
            return Config()

    @classmethod
    def _save_active_session_id(cls, session_id: int) -> None:
        """Update current_session_id in config file, preserving other values."""
        cls._ensure_dirs()
        raw = {}
        if CONFIG_PATH.exists():
            try:
                raw = json.loads(CONFIG_PATH.read_text())
            except json.JSONDecodeError:
                pass
        raw["current_session_id"] = session_id
        CONFIG_PATH.write_text(json.dumps(raw, indent=2))

    @classmethod
    def _read_session(cls, session_id: int) -> Session | None:
        """Read session from disk."""
        path = SESSIONS_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            return Session.model_validate_json(path.read_text())
        except Exception:
            return None

    @classmethod
    def _write_session(cls, session: Session) -> None:
        """Write session to disk."""
        cls._ensure_dirs()
        path = SESSIONS_DIR / f"{session.id}.json"
        path.write_text(session.model_dump_json(indent=2))

    @classmethod
    def _list_all_sessions(cls) -> list[Session]:
        """Load all sessions from disk, sorted by ID."""
        if not SESSIONS_DIR.exists():
            return []
        sessions = []
        for path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: int(p.stem)):
            try:
                sessions.append(Session.model_validate_json(path.read_text()))
            except Exception:
                continue
        return sessions

    @classmethod
    def _read_secrets(cls) -> dict[str, str]:
        """Read secrets from .env file, with environment variable overrides."""
        if not ENV_PATH.exists():
            return {}
        secrets = {}
        for key, value in dotenv_values(ENV_PATH).items():
            if value:
                secrets[key.lower()] = os.environ.get(key) or value
        return secrets

    @classmethod
    def _write_secret(cls, provider: str, key: str) -> None:
        """Write secret to .env file."""
        cls._ensure_dirs()
        if not ENV_PATH.exists():
            ENV_PATH.touch(mode=0o600)
        set_key(ENV_PATH, provider.lower(), key)
