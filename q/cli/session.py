import contextlib
import os
import sys
from pathlib import Path

import psutil
from dotenv import dotenv_values, set_key
from pydantic import BaseModel, Field

from ..message import Message
from .terminal import qinput, qprint

RESOURCES_DIR = Path.home() / ".q"
CONFIG_PATH = RESOURCES_DIR / "config.json"
SESSIONS_DIR = RESOURCES_DIR / "sessions"
ENV_PATH = RESOURCES_DIR / ".env"


class Config(BaseModel):
    """Config schema and defaults."""

    default_provider: str = "openai"
    code_lang: str = "python"


class Session(BaseModel):
    """Conversation session with message history."""

    pid_start: float
    command_char: str | None = None
    messages: list[Message] = Field(default_factory=list)


class StateManager:
    """Stateless manager for sessions, config, and keys."""

    # region Sessions

    @classmethod
    def load_session(cls) -> Session:
        """Load current session from disk, or create a new one."""
        pid = os.getppid()
        pid_start = cls._pid_start(pid)
        session = cls._pid_session(pid)
        if session and session.pid_start == pid_start:
            return session
        return Session(pid_start=pid_start)

    @classmethod
    def load_command_char(cls) -> str | None:
        """Load last command char from current session."""
        session = cls.load_session()
        return session.command_char

    @classmethod
    def load_messages(cls) -> list[Message]:
        """Load messages from current session."""
        session = cls.load_session()
        return session.messages

    @classmethod
    def save_session(cls, command_char: str | None, messages: list[Message]) -> None:
        """Save current session to disk."""
        pid = os.getppid()
        session = Session(pid_start=cls._pid_start(pid), command_char=command_char, messages=messages)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (SESSIONS_DIR / f"{pid}.json").write_text(session.model_dump_json(indent=2))

    @classmethod
    def reap_sessions(cls) -> None:
        """Delete stale sessions whose process has exited or been replaced."""
        for path in SESSIONS_DIR.glob("*.json"):
            if not path.stem.isdigit():
                continue
            pid = int(path.stem)
            session = cls._pid_session(pid)
            if not session or session.pid_start != cls._pid_start(pid):
                path.unlink(missing_ok=True)

    @classmethod
    def _pid_session(cls, pid: int) -> Session | None:
        """Get session for a process, or None if no such process."""
        with contextlib.suppress(Exception):
            return Session.model_validate_json((SESSIONS_DIR / f"{pid}.json").read_text())
        return None

    @classmethod
    def _pid_start(cls, pid: int) -> float | None:
        """Get start time for a process, or None if no such process."""
        with contextlib.suppress(psutil.Error):
            return round(psutil.Process(pid).create_time(), 2)
        return None

    # region Config

    @classmethod
    def load_config(cls) -> Config:
        """Load config from disk, or create default if missing."""
        if not CONFIG_PATH.exists():
            RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(Config().model_dump_json(indent=2))
        try:
            return Config.model_validate_json(CONFIG_PATH.read_text())
        except Exception:
            qprint(f"{CONFIG_PATH} is invalid, using defaults instead", color="yellow", file=sys.stderr)
            return Config()

    @classmethod
    def load_default_provider(cls) -> str:
        """Load default provider from config."""
        return cls.load_config().default_provider

    @classmethod
    def load_code_lang(cls) -> str:
        """Load code language from config."""
        return cls.load_config().code_lang

    # region Keys

    @classmethod
    def load_api_key(cls, provider: str) -> str:
        """Load API key from .env file. Prompts and saves if missing."""
        key = dotenv_values(ENV_PATH).get(provider.lower())
        if not key:
            key = qinput(f"{provider} API key not found. Enter key: ", secret=True).strip()
            # TODO: add load_provider_module(provider).validate_key(key)
            cls.save_api_key(provider, key)
        return key

    @classmethod
    def save_api_key(cls, provider: str, key: str) -> None:
        """Save API key to .env file."""
        RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
        ENV_PATH.touch(mode=0o600, exist_ok=True)
        set_key(ENV_PATH, provider.lower(), key)
