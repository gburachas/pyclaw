"""Session manager — persists conversation state."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from pyclaw.models import Message, Session

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions with JSON persistence."""

    def __init__(self, storage_dir: str):
        self._storage = Path(storage_dir).expanduser().resolve()
        self._storage.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Session] = {}
        self._load_sessions()

    def get_or_create(self, key: str) -> Session:
        if key not in self._sessions:
            self._sessions[key] = Session(key=key)
        return self._sessions[key]

    def add_message(self, session_key: str, role: str, content: str) -> None:
        session = self.get_or_create(session_key)
        session.messages.append(Message(role=role, content=content))
        session.updated = datetime.now()

    def add_full_message(self, session_key: str, msg: Message) -> None:
        session = self.get_or_create(session_key)
        session.messages.append(msg)
        session.updated = datetime.now()

    def get_history(self, key: str) -> list[Message]:
        session = self._sessions.get(key)
        return list(session.messages) if session else []

    def get_summary(self, key: str) -> str:
        session = self._sessions.get(key)
        return session.summary if session else ""

    def set_summary(self, key: str, summary: str) -> None:
        session = self.get_or_create(key)
        session.summary = summary
        session.updated = datetime.now()

    def truncate_history(self, key: str, keep_last: int) -> None:
        session = self._sessions.get(key)
        if session and len(session.messages) > keep_last:
            session.messages = session.messages[-keep_last:]
            session.updated = datetime.now()

    def set_history(self, key: str, history: list[Message]) -> None:
        session = self.get_or_create(key)
        session.messages = history
        session.updated = datetime.now()

    def clear(self, key: str) -> None:
        session = self._sessions.get(key)
        if session:
            session.messages = []
            session.summary = ""
            session.updated = datetime.now()

    def save(self, key: str) -> None:
        session = self._sessions.get(key)
        if session is None:
            return
        path = self._session_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = session.model_dump(mode="json")
        # Atomic write
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.rename(path)

    def save_all(self) -> None:
        for key in self._sessions:
            self.save(key)

    def _load_sessions(self) -> None:
        if not self._storage.exists():
            return
        for path in self._storage.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                session = Session.model_validate(data)
                self._sessions[session.key] = session
            except Exception as e:
                logger.warning("Failed to load session %s: %s", path, e)

    def _session_path(self, key: str) -> Path:
        safe_name = _sanitize_filename(key)
        return self._storage / f"{safe_name}.json"


def _sanitize_filename(name: str) -> str:
    """Convert a session key to a safe filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)
