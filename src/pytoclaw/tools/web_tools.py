"""Web search and fetch tools."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from pytoclaw.models import ToolResult
from pytoclaw.protocols import Tool

logger = logging.getLogger(__name__)


class WebFetchTool(Tool):
    """Fetch content from a URL."""

    def name(self) -> str:
        return "web_fetch"

    def description(self) -> str:
        return "Fetch the content of a web page by URL. Returns the page text."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
            },
            "required": ["url"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        url = args.get("url", "")
        if not url:
            return ToolResult.error("No URL provided")
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content = resp.text
                if len(content) > 50000:
                    content = content[:50000] + "\n... (content truncated)"
                return ToolResult.success(content)
        except Exception as e:
            return ToolResult.error(f"Error fetching URL: {e}")


class WebSearchTool(Tool):
    """Web search using DuckDuckGo (default, no API key needed)."""

    def __init__(self, brave_api_key: str = "", tavily_api_key: str = ""):
        self._brave_key = brave_api_key
        self._tavily_key = tavily_api_key

    def name(self) -> str:
        return "web_search"

    def description(self) -> str:
        return "Search the web for information. Returns search results with titles, URLs, and snippets."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        query = args.get("query", "")
        if not query:
            return ToolResult.error("No query provided")

        num = args.get("num_results", 5)

        # Try providers in priority order
        if self._brave_key:
            return await self._search_brave(query, num)
        if self._tavily_key:
            return await self._search_tavily(query, num)
        return await self._search_duckduckgo(query, num)

    async def _search_brave(self, query: str, num: int) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": num},
                    headers={"X-Subscription-Token": self._brave_key, "Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("web", {}).get("results", [])
                return self._format_results(results, "title", "url", "description")
        except Exception as e:
            return ToolResult.error(f"Brave search error: {e}")

    async def _search_tavily(self, query: str, num: int) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"query": query, "max_results": num, "api_key": self._tavily_key},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                return self._format_results(results, "title", "url", "content")
        except Exception as e:
            return ToolResult.error(f"Tavily search error: {e}")

    async def _search_duckduckgo(self, query: str, num: int) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "pytoclaw/0.1"},
                )
                # Simple parse — this is a fallback; for production use DDGS library
                text = resp.text
                return ToolResult.success(f"DuckDuckGo results for '{query}':\n{text[:5000]}")
        except Exception as e:
            return ToolResult.error(f"DuckDuckGo search error: {e}")

    @staticmethod
    def _format_results(
        results: list[dict[str, Any]],
        title_key: str,
        url_key: str,
        snippet_key: str,
    ) -> ToolResult:
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get(title_key, "")
            url = r.get(url_key, "")
            snippet = r.get(snippet_key, "")
            lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
        return ToolResult.success("\n\n".join(lines) if lines else "No results found")
