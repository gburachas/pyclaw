"""Memory store — long-term and daily notes."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryStore:
    """Manages agent memory files in the workspace."""

    def __init__(self, workspace: str):
        self._workspace = Path(workspace).expanduser().resolve()
        self._memory_dir = self._workspace / "memory"
        self._memory_file = self._memory_dir / "MEMORY.md"

    def read_long_term(self) -> str:
        if self._memory_file.exists():
            return self._memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._memory_file.write_text(content, encoding="utf-8")

    def read_today(self) -> str:
        path = self._today_path()
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def append_today(self, content: str) -> None:
        path = self._today_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)

    def get_memory_context(self) -> str:
        """Build memory context string for the system prompt."""
        parts = []
        long_term = self.read_long_term()
        if long_term:
            parts.append(f"## Long-term Memory\n{long_term}")
        today = self.read_today()
        if today:
            parts.append(f"## Today's Notes\n{today}")
        return "\n\n".join(parts)

    def _today_path(self) -> Path:
        now = datetime.now()
        month_dir = self._memory_dir / now.strftime("%Y%m")
        return month_dir / f"{now.strftime('%Y%m%d')}.md"
