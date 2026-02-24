"""Tool registry — manages and dispatches tool calls."""

from __future__ import annotations

import logging
from typing import Any, Callable

from pyclaw.models import ToolDefinition, ToolFunctionDefinition, ToolResult
from pyclaw.protocols import AsyncCallback, AsyncTool, ContextualTool, Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name()] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    async def execute(
        self,
        name: str,
        args: dict[str, Any],
        channel: str = "",
        chat_id: str = "",
        async_callback: AsyncCallback | None = None,
    ) -> ToolResult:
        """Execute a tool by name with arguments."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.error(f"Unknown tool: {name}")

        # Inject context if tool supports it
        if isinstance(tool, ContextualTool):
            tool.set_context(channel, chat_id)

        # Set async callback if tool supports it
        if isinstance(tool, AsyncTool) and async_callback:
            tool.set_callback(async_callback)

        try:
            return await tool.execute(args)
        except Exception as e:
            logger.exception("Tool '%s' failed", name)
            return ToolResult.error(f"Tool execution error: {e}")

    def get_definitions(self) -> list[ToolDefinition]:
        """Get tool definitions for LLM consumption."""
        defs = []
        for tool in self._tools.values():
            defs.append(
                ToolDefinition(
                    function=ToolFunctionDefinition(
                        name=tool.name(),
                        description=tool.description(),
                        parameters=tool.parameters(),
                    )
                )
            )
        return defs

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def count(self) -> int:
        return len(self._tools)
