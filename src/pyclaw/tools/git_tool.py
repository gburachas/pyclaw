"""Git tool — structured git operations via subprocess."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from pyclaw.models import ToolResult
from pyclaw.protocols import Tool


class GitTool(Tool):
    """Perform git operations with structured output."""

    def __init__(self, workspace: str) -> None:
        self._workspace = workspace

    def name(self) -> str:
        return "git"

    def description(self) -> str:
        return (
            "Execute git commands safely. "
            "Actions: status, log, diff, branch, add, commit, show. "
            "Destructive operations (push, reset --hard, force) are blocked."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "log", "diff", "branch", "add", "commit", "show"],
                    "description": "Git action to perform",
                },
                "args": {
                    "type": "string",
                    "description": "Additional arguments (e.g., file paths, commit message)",
                },
            },
            "required": ["action"],
        }

    _BLOCKED = {"push", "force-push", "reset --hard", "clean -f"}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        action = args.get("action", "")
        extra = args.get("args", "")

        # Block destructive operations
        combined = f"{action} {extra}".lower()
        for blocked in self._BLOCKED:
            if blocked in combined:
                return ToolResult.error(f"Blocked: '{blocked}' is not allowed for safety")

        cmd = self._build_command(action, extra)
        if cmd is None:
            return ToolResult.error(f"Unknown git action: {action}")

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=self._workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode(errors="replace")
            err_out = stderr.decode(errors="replace")

            if proc.returncode != 0:
                return ToolResult.error(f"git {action} failed (exit {proc.returncode}):\n{err_out or output}")

            result = output.strip()
            if err_out.strip():
                result += f"\n{err_out.strip()}"
            return ToolResult.success(result or "(no output)")
        except asyncio.TimeoutError:
            return ToolResult.error("Git command timed out after 30s")
        except Exception as e:
            return ToolResult.error(f"Git error: {e}")

    def _build_command(self, action: str, extra: str) -> str | None:
        safe_extra = extra.replace(";", "").replace("&&", "").replace("||", "").replace("|", "").replace("`", "")

        commands = {
            "status": "git status --porcelain",
            "log": f"git log --oneline -20 {safe_extra}".strip(),
            "diff": f"git diff {safe_extra}".strip(),
            "branch": f"git branch {safe_extra}".strip(),
            "add": f"git add {safe_extra}".strip(),
            "commit": f'git commit -m "{safe_extra}"' if safe_extra else None,
            "show": f"git show {safe_extra}".strip() if safe_extra else "git show --stat HEAD",
        }

        result = commands.get(action)
        if action == "commit" and not safe_extra:
            return None
        return result
