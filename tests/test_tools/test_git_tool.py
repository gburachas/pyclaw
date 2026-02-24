"""Tests for git tool."""

import os
import pytest

from pyclaw.tools.git_tool import GitTool


@pytest.fixture
def git_workspace(tmp_path):
    # Init a git repo in tmp_path
    os.system(f"cd {tmp_path} && git init -q && git config user.email test@test.com && git config user.name test")
    (tmp_path / "README.md").write_text("# test\n")
    os.system(f"cd {tmp_path} && git add . && git commit -q -m 'init'")
    return tmp_path


@pytest.fixture
def tool(git_workspace):
    return GitTool(str(git_workspace))


@pytest.mark.asyncio
async def test_status_clean(tool):
    result = await tool.execute({"action": "status"})
    assert not result.is_error
    # Clean repo should have empty or minimal output
    assert "error" not in result.for_llm.lower() or result.for_llm.strip() == ""


@pytest.mark.asyncio
async def test_log(tool):
    result = await tool.execute({"action": "log"})
    assert not result.is_error
    assert "init" in result.for_llm


@pytest.mark.asyncio
async def test_branch(tool):
    result = await tool.execute({"action": "branch"})
    assert not result.is_error


@pytest.mark.asyncio
async def test_push_blocked(tool):
    result = await tool.execute({"action": "push"})
    assert result.is_error
    assert "Blocked" in result.for_llm


@pytest.mark.asyncio
async def test_show(tool):
    result = await tool.execute({"action": "show"})
    assert not result.is_error
    assert "init" in result.for_llm
