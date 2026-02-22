"""Tests for file operation tools."""

import tempfile
from pathlib import Path

import pytest

from pytoclaw.tools.file_tools import (
    AppendFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)


@pytest.fixture
def workspace(tmp_path):
    return str(tmp_path)


@pytest.mark.asyncio
async def test_write_and_read(workspace):
    write = WriteFileTool(workspace)
    read = ReadFileTool(workspace)

    result = await write.execute({"path": "test.txt", "content": "hello world"})
    assert not result.is_error

    result = await read.execute({"path": "test.txt"})
    assert result.for_llm == "hello world"


@pytest.mark.asyncio
async def test_read_nonexistent(workspace):
    read = ReadFileTool(workspace)
    result = await read.execute({"path": "nope.txt"})
    assert result.is_error


@pytest.mark.asyncio
async def test_edit_file(workspace):
    write = WriteFileTool(workspace)
    edit = EditFileTool(workspace)
    read = ReadFileTool(workspace)

    await write.execute({"path": "test.txt", "content": "hello world"})
    result = await edit.execute({
        "path": "test.txt",
        "old_string": "world",
        "new_string": "pytoclaw",
    })
    assert not result.is_error

    result = await read.execute({"path": "test.txt"})
    assert result.for_llm == "hello pytoclaw"


@pytest.mark.asyncio
async def test_edit_not_found(workspace):
    edit = EditFileTool(workspace)
    result = await edit.execute({
        "path": "nope.txt",
        "old_string": "a",
        "new_string": "b",
    })
    assert result.is_error


@pytest.mark.asyncio
async def test_append_file(workspace):
    write = WriteFileTool(workspace)
    append = AppendFileTool(workspace)
    read = ReadFileTool(workspace)

    await write.execute({"path": "test.txt", "content": "line1\n"})
    await append.execute({"path": "test.txt", "content": "line2\n"})

    result = await read.execute({"path": "test.txt"})
    assert result.for_llm == "line1\nline2\n"


@pytest.mark.asyncio
async def test_list_dir(workspace):
    write = WriteFileTool(workspace)
    await write.execute({"path": "a.txt", "content": "a"})
    await write.execute({"path": "b.txt", "content": "b"})

    list_dir = ListDirTool(workspace)
    result = await list_dir.execute({"path": "."})
    assert "a.txt" in result.for_llm
    assert "b.txt" in result.for_llm


@pytest.mark.asyncio
async def test_workspace_restriction(workspace):
    read = ReadFileTool(workspace, restrict=True)
    result = await read.execute({"path": "/etc/passwd"})
    assert result.is_error
    assert "outside workspace" in result.for_llm.lower()
