"""Shell execution tool with safety guards."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from pyclaw.models import ToolResult
from pyclaw.protocols import Tool

logger = logging.getLogger(__name__)

# Default dangerous command patterns (from Go implementation)
DEFAULT_DENY_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r"rm\s+-rf\s+\.\.",
    r"mkfs\.",
    r"format\s+[a-zA-Z]:",
    r"dd\s+if=",
    r">\s*/dev/sd",
    r"shutdown",
    r"reboot",
    r"init\s+[0-6]",
    r":()\{.*\|.*&.*\};:",  # Fork bomb
    r"curl.*\|\s*(ba)?sh",
    r"wget.*\|\s*(ba)?sh",
    r"chmod\s+-R\s+777\s+/",
    r"chown\s+-R.*\s+/",
    r"sudo\s+rm",
    r"sudo\s+dd",
    r">\s*/etc/",
    r"mv\s+/",
    r"echo.*>\s*/etc/passwd",
]


class ExecTool(Tool):
    """Execute shell commands with safety guards."""

    def __init__(
        self,
        workspace: str,
        restrict_to_workspace: bool = True,
        timeout_seconds: int = 120,
        custom_deny_patterns: list[str] | None = None,
        enable_deny_patterns: bool = True,
    ):
        self._workspace = Path(workspace).expanduser().resolve()
        self._restrict = restrict_to_workspace
        self._timeout = timeout_seconds
        self._enable_deny = enable_deny_patterns
        patterns = DEFAULT_DENY_PATTERNS + (custom_deny_patterns or [])
        self._deny_patterns = [re.compile(p, re.IGNORECASE) for p in patterns] if enable_deny_patterns else []

    def name(self) -> str:
        return "exec"

    def description(self) -> str:
        return (
            "Execute a shell command and return its output. "
            "Commands run in the workspace directory."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 120)",
                },
            },
            "required": ["command"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        command = args.get("command", "").strip()
        if not command:
            return ToolResult.error("No command provided")

        timeout = args.get("timeout", self._timeout)

        # Safety check
        denied = self._check_denied(command)
        if denied:
            return ToolResult.error(f"Command blocked by safety guard: {denied}")

        cwd = str(self._workspace)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            output_parts = []
            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                output_parts.append(f"[stderr]\n{stderr.decode('utf-8', errors='replace')}")

            output = "\n".join(output_parts).strip()
            if proc.returncode != 0:
                output = f"[exit code: {proc.returncode}]\n{output}"

            # Truncate very long output
            if len(output) > 30000:
                output = output[:30000] + "\n... (output truncated)"

            return ToolResult.success(output if output else "(no output)")

        except asyncio.TimeoutError:
            return ToolResult.error(f"Command timed out after {timeout} seconds")
        except Exception as e:
            return ToolResult.error(f"Error executing command: {e}")

    def _check_denied(self, command: str) -> str | None:
        """Check if command matches any deny pattern."""
        for pattern in self._deny_patterns:
            if pattern.search(command):
                return pattern.pattern
        return None
