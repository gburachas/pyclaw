"""Cron service — scheduled job execution."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Coroutine

from croniter import croniter

logger = logging.getLogger(__name__)

JobHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, str | None]]


class CronService:
    """Manages and executes scheduled jobs."""

    def __init__(self, store_path: str):
        self._store_path = Path(store_path).expanduser().resolve()
        self._jobs_file = self._store_path / "jobs.json"
        self._jobs: list[dict[str, Any]] = []
        self._handler: JobHandler | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._load_jobs()

    def set_handler(self, handler: JobHandler) -> None:
        self._handler = handler

    def start(self) -> None:
        self._running = True
        self._task = asyncio.ensure_future(self._run_loop())
        logger.info("Cron service started (%d jobs)", len(self._jobs))

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    def add_job(
        self,
        name: str,
        schedule: dict[str, Any],
        message: str = "",
        command: str = "",
        deliver: bool = True,
        channel: str = "",
        chat_id: str = "",
    ) -> dict[str, Any]:
        """Create a new scheduled job."""
        job_id = os.urandom(8).hex()
        now_ms = int(time.time() * 1000)

        job: dict[str, Any] = {
            "id": job_id,
            "name": name,
            "enabled": True,
            "schedule": schedule,
            "payload": {
                "kind": "agent_turn",
                "message": message,
                "command": command,
                "deliver": deliver,
                "channel": channel,
                "to": chat_id,
            },
            "state": {
                "next_run_ms": self._compute_next_run(schedule, now_ms),
                "last_run_ms": None,
                "last_status": None,
                "last_error": None,
            },
            "created_ms": now_ms,
            "updated_ms": now_ms,
            "delete_after_run": schedule.get("kind") == "at",
        }

        self._jobs.append(job)
        self._save_jobs()
        return job

    def remove_job(self, job_id: str) -> bool:
        before = len(self._jobs)
        self._jobs = [j for j in self._jobs if not j["id"].startswith(job_id)]
        if len(self._jobs) < before:
            self._save_jobs()
            return True
        return False

    def enable_job(self, job_id: str, enabled: bool) -> dict[str, Any] | None:
        for job in self._jobs:
            if job["id"].startswith(job_id):
                job["enabled"] = enabled
                job["updated_ms"] = int(time.time() * 1000)
                if enabled:
                    job["state"]["next_run_ms"] = self._compute_next_run(
                        job["schedule"], int(time.time() * 1000)
                    )
                self._save_jobs()
                return job
        return None

    def list_jobs(self, include_disabled: bool = True) -> list[dict[str, Any]]:
        if include_disabled:
            return list(self._jobs)
        return [j for j in self._jobs if j.get("enabled", True)]

    async def _run_loop(self) -> None:
        while self._running:
            await asyncio.sleep(1)
            if not self._running:
                break
            await self._check_jobs()

    async def _check_jobs(self) -> None:
        now_ms = int(time.time() * 1000)
        to_delete = []

        for job in self._jobs:
            if not job.get("enabled", True):
                continue
            next_run = job.get("state", {}).get("next_run_ms")
            if next_run is None or next_run > now_ms:
                continue

            # Mark as running (prevent re-execution)
            job["state"]["next_run_ms"] = None

            try:
                if self._handler:
                    result = await self._handler(job)
                    job["state"]["last_status"] = "ok"
                    job["state"]["last_error"] = None
                else:
                    job["state"]["last_status"] = "error"
                    job["state"]["last_error"] = "No handler configured"
            except Exception as e:
                job["state"]["last_status"] = "error"
                job["state"]["last_error"] = str(e)

            job["state"]["last_run_ms"] = now_ms

            if job.get("delete_after_run"):
                to_delete.append(job["id"])
            else:
                job["state"]["next_run_ms"] = self._compute_next_run(
                    job["schedule"], now_ms
                )

        if to_delete:
            self._jobs = [j for j in self._jobs if j["id"] not in to_delete]

        self._save_jobs()

    def _compute_next_run(self, schedule: dict[str, Any], now_ms: int) -> int | None:
        kind = schedule.get("kind", "")
        if kind == "at":
            return schedule.get("at_ms")
        elif kind == "every":
            every_ms = schedule.get("every_ms", 60000)
            return now_ms + every_ms
        elif kind == "cron":
            expr = schedule.get("expr", "")
            try:
                cron = croniter(expr, time.time())
                next_time = cron.get_next(float)
                return int(next_time * 1000)
            except Exception:
                logger.warning("Invalid cron expression: %s", expr)
                return None
        return None

    def _load_jobs(self) -> None:
        if self._jobs_file.exists():
            try:
                data = json.loads(self._jobs_file.read_text(encoding="utf-8"))
                self._jobs = data if isinstance(data, list) else []
            except Exception:
                logger.warning("Failed to load cron jobs")
                self._jobs = []

    def _save_jobs(self) -> None:
        self._store_path.mkdir(parents=True, exist_ok=True)
        tmp = self._jobs_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._jobs, indent=2, default=str), encoding="utf-8")
        tmp.rename(self._jobs_file)
