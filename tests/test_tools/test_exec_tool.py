"""Tests for exec tool."""

import pytest

from pyclaw.tools.exec_tool import ExecTool


@pytest.fixture
def exec_tool(tmp_path):
    return ExecTool(str(tmp_path))


@pytest.mark.asyncio
async def test_echo(exec_tool):
    result = await exec_tool.execute({"command": "echo hello"})
    assert result.for_llm.strip() == "hello"
    assert not result.is_error


@pytest.mark.asyncio
async def test_dangerous_command_blocked(exec_tool):
    result = await exec_tool.execute({"command": "rm -rf /"})
    assert result.is_error
    assert "blocked" in result.for_llm.lower()


@pytest.mark.asyncio
async def test_empty_command(exec_tool):
    result = await exec_tool.execute({"command": ""})
    assert result.is_error


@pytest.mark.asyncio
async def test_nonzero_exit(exec_tool):
    result = await exec_tool.execute({"command": "false"})
    assert "exit code" in result.for_llm.lower()


@pytest.mark.asyncio
async def test_deny_patterns_disabled(tmp_path):
    tool = ExecTool(str(tmp_path), enable_deny_patterns=False)
    # Should not block even dangerous-looking commands
    # (we test with a harmless command that matches a pattern)
    result = await tool.execute({"command": "echo 'rm -rf / is bad'"})
    assert not result.is_error
