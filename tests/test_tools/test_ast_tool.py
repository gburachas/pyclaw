"""Tests for AST analysis tool."""

import os
import pytest

from pyclaw.tools.ast_tool import ASTAnalyzeTool


@pytest.fixture
def workspace(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "\n"
        "class MyClass:\n"
        "    def method_one(self, x):\n"
        "        if x > 0:\n"
        "            return x\n"
        "        return 0\n"
        "\n"
        "    async def async_method(self, y):\n"
        "        for i in range(y):\n"
        "            pass\n"
        "\n"
        "def standalone(a, b):\n"
        "    return a + b\n"
    )
    return tmp_path


@pytest.fixture
def tool(workspace):
    return ASTAnalyzeTool(str(workspace))


@pytest.mark.asyncio
async def test_outline(tool):
    result = await tool.execute({"path": "sample.py", "action": "outline"})
    assert "MyClass" in result.for_llm
    assert "method_one" in result.for_llm
    assert "async_method" in result.for_llm
    assert "standalone" in result.for_llm


@pytest.mark.asyncio
async def test_imports(tool):
    result = await tool.execute({"path": "sample.py", "action": "imports"})
    assert "import os" in result.for_llm
    assert "from pathlib import Path" in result.for_llm


@pytest.mark.asyncio
async def test_complexity(tool):
    result = await tool.execute({"path": "sample.py", "action": "complexity"})
    assert "functions: 3" in result.for_llm
    assert "classes: 1" in result.for_llm
    assert "branches: 1" in result.for_llm
    assert "loops: 1" in result.for_llm


@pytest.mark.asyncio
async def test_search(tool):
    result = await tool.execute({"path": "sample.py", "action": "search", "query": "method"})
    assert "method_one" in result.for_llm
    assert "async_method" in result.for_llm


@pytest.mark.asyncio
async def test_search_no_match(tool):
    result = await tool.execute({"path": "sample.py", "action": "search", "query": "zzzzz"})
    assert "No definitions" in result.for_llm


@pytest.mark.asyncio
async def test_file_not_found(tool):
    result = await tool.execute({"path": "nonexistent.py", "action": "outline"})
    assert result.is_error


@pytest.mark.asyncio
async def test_workspace_restriction(tool):
    result = await tool.execute({"path": "../../etc/passwd", "action": "outline"})
    assert result.is_error
