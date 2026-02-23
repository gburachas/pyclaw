"""AST-based code analysis tool using Python's ast module."""

from __future__ import annotations

import ast
import os
from typing import Any

from pytoclaw.models import ToolResult
from pytoclaw.protocols import Tool


class ASTAnalyzeTool(Tool):
    """Analyze Python source files using AST parsing."""

    def __init__(self, workspace: str) -> None:
        self._workspace = workspace

    def name(self) -> str:
        return "ast_analyze"

    def description(self) -> str:
        return (
            "Analyze Python source code structure. "
            "Actions: outline (list classes/functions), imports (list imports), "
            "complexity (count branches/loops), search (find definitions by name)."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
                "action": {
                    "type": "string",
                    "enum": ["outline", "imports", "complexity", "search"],
                    "description": "Analysis action to perform",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for 'search' action)",
                },
            },
            "required": ["path", "action"],
        }

    def _resolve(self, path: str) -> str:
        full = os.path.normpath(os.path.join(self._workspace, path))
        if not full.startswith(os.path.normpath(self._workspace)):
            raise PermissionError("Path outside workspace")
        return full

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        path = args.get("path", "")
        action = args.get("action", "outline")

        try:
            full_path = self._resolve(path)
        except PermissionError as e:
            return ToolResult.error(str(e))

        if not os.path.isfile(full_path):
            return ToolResult.error(f"File not found: {path}")

        try:
            with open(full_path) as f:
                source = f.read()
            tree = ast.parse(source, filename=path)
        except SyntaxError as e:
            return ToolResult.error(f"Syntax error: {e}")

        if action == "outline":
            return ToolResult.success(self._outline(tree))
        elif action == "imports":
            return ToolResult.success(self._imports(tree))
        elif action == "complexity":
            return ToolResult.success(self._complexity(tree))
        elif action == "search":
            query = args.get("query", "")
            return ToolResult.success(self._search(tree, query))
        else:
            return ToolResult.error(f"Unknown action: {action}")

    def _outline(self, tree: ast.AST) -> str:
        lines = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                lines.append(f"class {node.name} (line {node.lineno})")
                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        args = [a.arg for a in item.args.args if a.arg != "self"]
                        sig = ", ".join(args)
                        prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                        lines.append(f"  {prefix}def {item.name}({sig}) (line {item.lineno})")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                args = [a.arg for a in node.args.args]
                sig = ", ".join(args)
                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                lines.append(f"{prefix}def {node.name}({sig}) (line {node.lineno})")
        return "\n".join(lines) if lines else "No classes or functions found."

    def _imports(self, tree: ast.AST) -> str:
        lines = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    lines.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    lines.append(f"from {module} import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
        return "\n".join(lines) if lines else "No imports found."

    def _complexity(self, tree: ast.AST) -> str:
        stats = {"functions": 0, "classes": 0, "branches": 0, "loops": 0, "try_except": 0, "lines": 0}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                stats["functions"] += 1
            elif isinstance(node, ast.ClassDef):
                stats["classes"] += 1
            elif isinstance(node, ast.If):
                stats["branches"] += 1
            elif isinstance(node, ast.For | ast.While | ast.AsyncFor):
                stats["loops"] += 1
            elif isinstance(node, ast.Try | ast.ExceptHandler):
                stats["try_except"] += 1
        # Count non-empty lines
        if hasattr(tree, 'body') and tree.body:
            last = max((getattr(n, 'end_lineno', getattr(n, 'lineno', 0)) for n in ast.walk(tree) if hasattr(n, 'lineno')), default=0)
            stats["lines"] = last
        parts = [f"{k}: {v}" for k, v in stats.items()]
        return "\n".join(parts)

    def _search(self, tree: ast.AST, query: str) -> str:
        if not query:
            return "No query provided."
        query_lower = query.lower()
        results = []
        for node in ast.walk(tree):
            name = getattr(node, "name", None)
            if name and query_lower in name.lower():
                kind = type(node).__name__
                line = getattr(node, "lineno", "?")
                results.append(f"{kind} '{name}' at line {line}")
        return "\n".join(results) if results else f"No definitions matching '{query}'."
