"""Tests for tool registry."""

from typing import Any

import pytest

from pyclaw.models import ToolResult
from pyclaw.protocols import Tool
from pyclaw.tools.registry import ToolRegistry


class DummyTool(Tool):
    def name(self) -> str:
        return "dummy"

    def description(self) -> str:
        return "A dummy tool for testing"

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"x": {"type": "string"}}}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult.success(f"got: {args.get('x', '')}")


@pytest.mark.asyncio
async def test_register_and_execute():
    registry = ToolRegistry()
    registry.register(DummyTool())

    assert registry.count() == 1
    assert "dummy" in registry.list_names()

    result = await registry.execute("dummy", {"x": "hello"})
    assert result.for_llm == "got: hello"


@pytest.mark.asyncio
async def test_unknown_tool():
    registry = ToolRegistry()
    result = await registry.execute("nonexistent", {})
    assert result.is_error


def test_get_definitions():
    registry = ToolRegistry()
    registry.register(DummyTool())
    defs = registry.get_definitions()
    assert len(defs) == 1
    assert defs[0].function.name == "dummy"
