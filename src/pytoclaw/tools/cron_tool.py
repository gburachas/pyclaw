"""Cron tool — schedule tasks for future execution."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from pytoclaw.models import ToolResult
from pytoclaw.protocols import ContextualTool

logger = logging.getLogger(__name__)


class CronTool(ContextualTool):
    """Schedule one-time or recurring tasks."""

    def __init__(self, store_path: str = ""):
        self._store_path = store_path
        self._channel = ""
        self._chat_id = ""
        # Lazy import of CronService to avoid circular deps
        self._service: Any = None

    def name(self) -> str:
        return "cron"

    def description(self) -> str:
        return (
            "Schedule tasks for future execution. Supports one-time delays, "
            "recurring intervals, and cron expressions."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "remove", "enable", "disable"],
                    "description": "Action to perform",
                },
                "name": {"type": "string", "description": "Job name (for add)"},
                "message": {"type": "string", "description": "Task prompt (for add)"},
                "command": {"type": "string", "description": "Shell command to run (for add)"},
                "at_seconds": {
                    "type": "integer",
                    "description": "One-time delay in seconds from now (for add)",
                },
                "every_seconds": {
                    "type": "integer",
                    "description": "Recurring interval in seconds (for add)",
                },
                "cron_expr": {
                    "type": "string",
                    "description": "Cron expression e.g. '0 9 * * *' (for add)",
                },
                "deliver": {
                    "type": "boolean",
                    "description": "Send result directly to channel (default true)",
                    "default": True,
                },
                "job_id": {"type": "string", "description": "Job ID (for remove/enable/disable)"},
            },
            "required": ["action"],
        }

    def set_context(self, channel: str, chat_id: str) -> None:
        self._channel = channel
        self._chat_id = chat_id

    def set_service(self, service: Any) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        action = args.get("action", "")

        if self._service is None:
            return ToolResult.error("Cron service not initialized")

        if action == "add":
            return await self._add_job(args)
        elif action == "list":
            return self._list_jobs()
        elif action == "remove":
            return self._remove_job(args.get("job_id", ""))
        elif action == "enable":
            return self._toggle_job(args.get("job_id", ""), True)
        elif action == "disable":
            return self._toggle_job(args.get("job_id", ""), False)
        else:
            return ToolResult.error(f"Unknown action: {action}")

    async def _add_job(self, args: dict[str, Any]) -> ToolResult:
        name = args.get("name", "Unnamed job")
        message = args.get("message", "")
        command = args.get("command", "")
        deliver = args.get("deliver", True)

        if not message and not command:
            return ToolResult.error("Either 'message' or 'command' is required")

        # Determine schedule kind
        at_seconds = args.get("at_seconds")
        every_seconds = args.get("every_seconds")
        cron_expr = args.get("cron_expr")

        schedule: dict[str, Any] = {}
        if at_seconds:
            schedule = {"kind": "at", "at_ms": int((time.time() + at_seconds) * 1000)}
        elif every_seconds:
            schedule = {"kind": "every", "every_ms": every_seconds * 1000}
        elif cron_expr:
            schedule = {"kind": "cron", "expr": cron_expr}
        else:
            return ToolResult.error(
                "One of at_seconds, every_seconds, or cron_expr is required"
            )

        job = self._service.add_job(
            name=name,
            schedule=schedule,
            message=message,
            command=command,
            deliver=deliver,
            channel=self._channel,
            chat_id=self._chat_id,
        )
        return ToolResult.success(f"Job '{name}' created with ID: {job['id']}")

    def _list_jobs(self) -> ToolResult:
        jobs = self._service.list_jobs()
        if not jobs:
            return ToolResult.success("No scheduled jobs.")
        lines = []
        for job in jobs:
            status = "enabled" if job.get("enabled", True) else "disabled"
            lines.append(f"- {job['name']} (ID: {job['id']}, {status})")
        return ToolResult.success("\n".join(lines))

    def _remove_job(self, job_id: str) -> ToolResult:
        if not job_id:
            return ToolResult.error("job_id is required")
        if self._service.remove_job(job_id):
            return ToolResult.success(f"Job {job_id} removed.")
        return ToolResult.error(f"Job {job_id} not found.")

    def _toggle_job(self, job_id: str, enabled: bool) -> ToolResult:
        if not job_id:
            return ToolResult.error("job_id is required")
        job = self._service.enable_job(job_id, enabled)
        if job:
            state = "enabled" if enabled else "disabled"
            return ToolResult.success(f"Job {job_id} {state}.")
        return ToolResult.error(f"Job {job_id} not found.")
