"""Heartbeat service — periodic task execution from HEARTBEAT.md."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

HeartbeatHandler = Callable[[str, str, str], Coroutine[Any, Any, str | None]]

DEFAULT_HEARTBEAT = """# Heartbeat Tasks

<!-- Tasks listed here will be executed periodically -->
<!-- Remove the comment markers to activate a task -->

<!-- - Check system status and report any issues -->
<!-- - Review memory for any pending reminders -->
"""


class HeartbeatService:
    """Periodically reads HEARTBEAT.md and executes tasks."""

    def __init__(
        self,
        workspace: str,
        interval_minutes: int = 30,
        enabled: bool = False,
    ):
        self._workspace = Path(workspace).expanduser().resolve()
        self._heartbeat_file = self._workspace / "HEARTBEAT.md"
        self._log_file = self._workspace / "heartbeat.log"
        self._interval = max(interval_minutes, 5) * 60  # Min 5 minutes
        self._enabled = enabled
        self._handler: HeartbeatHandler | None = None
        self._last_channel = ""
        self._last_chat_id = ""
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def set_handler(self, handler: HeartbeatHandler) -> None:
        self._handler = handler

    def set_last_channel(self, channel: str, chat_id: str) -> None:
        self._last_channel = channel
        self._last_chat_id = chat_id

    def start(self) -> None:
        if not self._enabled:
            return
        self._running = True
        self._ensure_heartbeat_file()
        self._task = asyncio.ensure_future(self._run_loop())
        logger.info("Heartbeat service started (interval: %ds)", self._interval)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    def is_running(self) -> bool:
        return self._running

    async def _run_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._interval)
            if not self._running:
                break
            try:
                await self._execute_heartbeat()
            except Exception:
                logger.exception("Heartbeat execution failed")

    async def _execute_heartbeat(self) -> None:
        content = self._read_heartbeat()
        if not content or not content.strip():
            return

        # Skip if all lines are comments
        active_lines = [
            line for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("<!--")
        ]
        if not active_lines:
            return

        if self._handler is None:
            logger.warning("No heartbeat handler configured")
            return

        prompt = f"Execute these heartbeat tasks:\n{content}"
        self._log("INFO", "Executing heartbeat tasks")

        result = await self._handler(prompt, self._last_channel, self._last_chat_id)
        if result:
            self._log("INFO", f"Heartbeat result: {result[:200]}")

    def _read_heartbeat(self) -> str:
        if self._heartbeat_file.exists():
            return self._heartbeat_file.read_text(encoding="utf-8")
        return ""

    def _ensure_heartbeat_file(self) -> None:
        if not self._heartbeat_file.exists():
            self._heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
            self._heartbeat_file.write_text(DEFAULT_HEARTBEAT, encoding="utf-8")

    def _log(self, level: str, message: str) -> None:
        timestamp = datetime.now().isoformat()
        entry = f"{timestamp} [{level}] {message}\n"
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass
