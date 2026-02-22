"""File operation tools: read_file, write_file, edit_file, append_file, list_dir."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pytoclaw.models import ToolResult
from pytoclaw.protocols import Tool


class ReadFileTool(Tool):
    def __init__(self, workspace: str, restrict: bool = True):
        self._workspace = Path(workspace).expanduser().resolve()
        self._restrict = restrict

    def name(self) -> str:
        return "read_file"

    def description(self) -> str:
        return "Read the contents of a file. Returns the file content as text."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
            },
            "required": ["path"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        path = self._resolve(args.get("path", ""))
        if path is None:
            return ToolResult.error("Path is outside workspace")
        if not path.exists():
            return ToolResult.error(f"File not found: {path}")
        if not path.is_file():
            return ToolResult.error(f"Not a file: {path}")
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return ToolResult.success(content)
        except Exception as e:
            return ToolResult.error(f"Error reading file: {e}")

    def _resolve(self, raw: str) -> Path | None:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = self._workspace / p
        p = p.resolve()
        if self._restrict and not str(p).startswith(str(self._workspace)):
            return None
        return p


class WriteFileTool(Tool):
    def __init__(self, workspace: str, restrict: bool = True):
        self._workspace = Path(workspace).expanduser().resolve()
        self._restrict = restrict

    def name(self) -> str:
        return "write_file"

    def description(self) -> str:
        return "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write to the file"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        path = self._resolve(args.get("path", ""))
        if path is None:
            return ToolResult.error("Path is outside workspace")
        content = args.get("content", "")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult.success(f"Written {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult.error(f"Error writing file: {e}")

    def _resolve(self, raw: str) -> Path | None:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = self._workspace / p
        p = p.resolve()
        if self._restrict and not str(p).startswith(str(self._workspace)):
            return None
        return p


class EditFileTool(Tool):
    def __init__(self, workspace: str, restrict: bool = True):
        self._workspace = Path(workspace).expanduser().resolve()
        self._restrict = restrict

    def name(self) -> str:
        return "edit_file"

    def description(self) -> str:
        return "Edit a file by replacing an old string with a new string."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to edit"},
                "old_string": {"type": "string", "description": "The exact string to find and replace"},
                "new_string": {"type": "string", "description": "The replacement string"},
            },
            "required": ["path", "old_string", "new_string"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        path = self._resolve(args.get("path", ""))
        if path is None:
            return ToolResult.error("Path is outside workspace")
        if not path.exists():
            return ToolResult.error(f"File not found: {path}")
        old = args.get("old_string", "")
        new = args.get("new_string", "")
        try:
            content = path.read_text(encoding="utf-8")
            if old not in content:
                return ToolResult.error("old_string not found in file")
            count = content.count(old)
            if count > 1:
                return ToolResult.error(
                    f"old_string appears {count} times. Provide more context to make it unique."
                )
            content = content.replace(old, new, 1)
            path.write_text(content, encoding="utf-8")
            return ToolResult.success("File edited successfully")
        except Exception as e:
            return ToolResult.error(f"Error editing file: {e}")

    def _resolve(self, raw: str) -> Path | None:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = self._workspace / p
        p = p.resolve()
        if self._restrict and not str(p).startswith(str(self._workspace)):
            return None
        return p


class AppendFileTool(Tool):
    def __init__(self, workspace: str, restrict: bool = True):
        self._workspace = Path(workspace).expanduser().resolve()
        self._restrict = restrict

    def name(self) -> str:
        return "append_file"

    def description(self) -> str:
        return "Append content to the end of a file."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to append"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        path = self._resolve(args.get("path", ""))
        if path is None:
            return ToolResult.error("Path is outside workspace")
        content = args.get("content", "")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            return ToolResult.success(f"Appended {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult.error(f"Error appending to file: {e}")

    def _resolve(self, raw: str) -> Path | None:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = self._workspace / p
        p = p.resolve()
        if self._restrict and not str(p).startswith(str(self._workspace)):
            return None
        return p


class ListDirTool(Tool):
    def __init__(self, workspace: str, restrict: bool = True):
        self._workspace = Path(workspace).expanduser().resolve()
        self._restrict = restrict

    def name(self) -> str:
        return "list_dir"

    def description(self) -> str:
        return "List files and directories in a given path."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: workspace root)",
                    "default": ".",
                },
            },
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        raw = args.get("path", ".")
        path = self._resolve(raw)
        if path is None:
            return ToolResult.error("Path is outside workspace")
        if not path.exists():
            return ToolResult.error(f"Directory not found: {path}")
        if not path.is_dir():
            return ToolResult.error(f"Not a directory: {path}")
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            lines = []
            for entry in entries:
                suffix = "/" if entry.is_dir() else ""
                lines.append(f"{entry.name}{suffix}")
            return ToolResult.success("\n".join(lines) if lines else "(empty directory)")
        except Exception as e:
            return ToolResult.error(f"Error listing directory: {e}")

    def _resolve(self, raw: str) -> Path | None:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = self._workspace / p
        p = p.resolve()
        if self._restrict and not str(p).startswith(str(self._workspace)):
            return None
        return p
