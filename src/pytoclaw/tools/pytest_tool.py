"""Pytest integration tool — run tests with structured output."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from pytoclaw.models import ToolResult
from pytoclaw.protocols import Tool


class PytestTool(Tool):
    """Run pytest with structured JSON output."""

    def __init__(self, workspace: str) -> None:
        self._workspace = workspace

    def name(self) -> str:
        return "pytest"

    def description(self) -> str:
        return (
            "Run Python tests using pytest. Returns structured results with "
            "pass/fail counts and failure details. Can target specific files or test names."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Test file or directory (relative to workspace). Default: 'tests/'",
                },
                "filter": {
                    "type": "string",
                    "description": "Test name filter (-k expression)",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Show verbose output",
                },
            },
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        path = args.get("path", "tests/")
        test_filter = args.get("filter", "")
        verbose = args.get("verbose", False)

        # Build command
        cmd_parts = ["python", "-m", "pytest", path, "--tb=short", "-q"]
        if test_filter:
            safe_filter = test_filter.replace(";", "").replace("&&", "")
            cmd_parts.extend(["-k", safe_filter])
        if verbose:
            cmd_parts.append("-v")

        cmd = " ".join(cmd_parts)

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=self._workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode(errors="replace")
            err_output = stderr.decode(errors="replace")

            # Parse summary line
            full_output = output + err_output
            summary = self._parse_summary(full_output)
            summary["exit_code"] = proc.returncode
            summary["output"] = full_output[-3000:] if len(full_output) > 3000 else full_output

            if proc.returncode == 0:
                return ToolResult.success(
                    f"PASSED: {summary.get('passed', '?')} tests passed\n\n{summary['output']}"
                )
            else:
                return ToolResult.success(
                    f"FAILED: {summary.get('failed', '?')} failed, "
                    f"{summary.get('passed', '?')} passed\n\n{summary['output']}"
                )

        except asyncio.TimeoutError:
            return ToolResult.error("Tests timed out after 120s")
        except Exception as e:
            return ToolResult.error(f"Pytest error: {e}")

    def _parse_summary(self, output: str) -> dict[str, Any]:
        """Extract pass/fail counts from pytest output."""
        summary: dict[str, Any] = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
        for line in output.splitlines():
            line = line.strip()
            # Match lines like "5 passed", "2 failed, 3 passed"
            if "passed" in line or "failed" in line or "error" in line:
                import re
                for match in re.finditer(r"(\d+)\s+(passed|failed|error|skipped|warning)", line):
                    count = int(match.group(1))
                    kind = match.group(2)
                    if kind == "passed":
                        summary["passed"] = count
                    elif kind == "failed":
                        summary["failed"] = count
                    elif kind == "error":
                        summary["errors"] = count
                    elif kind == "skipped":
                        summary["skipped"] = count
        return summary
