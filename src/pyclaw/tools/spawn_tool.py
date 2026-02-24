"""Spawn tool — create subagent for background work."""

from __future__ import annotations

import logging
from typing import Any, Callable

from pyclaw.models import ToolResult
from pyclaw.protocols import AsyncCallback, AsyncTool, ContextualTool

logger = logging.getLogger(__name__)


class SpawnTool(ContextualTool, AsyncTool):
    """Spawn a subagent to handle a task in the background."""

    def __init__(self) -> None:
        self._channel = ""
        self._chat_id = ""
        self._callback: AsyncCallback | None = None
        self._allowlist_checker: Callable[[str], bool] | None = None

    def name(self) -> str:
        return "spawn"

    def description(self) -> str:
        return (
            "Spawn a background subagent to handle a complex or long-running task. "
            "The subagent runs independently and reports results when done."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Description of the task for the subagent to perform",
                },
                "label": {
                    "type": "string",
                    "description": "Short label for the spawned task",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Optional: target agent ID to handle the task",
                },
            },
            "required": ["task"],
        }

    def set_context(self, channel: str, chat_id: str) -> None:
        self._channel = channel
        self._chat_id = chat_id

    def set_callback(self, callback: AsyncCallback) -> None:
        self._callback = callback

    def set_allowlist_checker(self, checker: Callable[[str], bool]) -> None:
        self._allowlist_checker = checker

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        task = args.get("task", "").strip()
        if not task:
            return ToolResult.error("No task provided")

        label = args.get("label", task[:50])
        agent_id = args.get("agent_id", "")

        # Check allowlist if agent_id specified
        if agent_id and self._allowlist_checker:
            if not self._allowlist_checker(agent_id):
                return ToolResult.error(
                    f"Agent '{agent_id}' is not in the allowed subagent list"
                )

        logger.info("Spawning subagent: %s (agent=%s)", label, agent_id or "default")

        return ToolResult.async_result(
            f"Subagent spawned for task: {label}. "
            "It will run in the background and report results when complete."
        )
