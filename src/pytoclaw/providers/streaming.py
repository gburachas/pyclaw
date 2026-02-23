"""Streaming LLM output support."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Callable

from pytoclaw.models import LLMResponse, Message, ToolCall, ToolDefinition, UsageInfo

logger = logging.getLogger(__name__)

# Callback type for streaming chunks
StreamCallback = Callable[[str], Any]


async def stream_openai_response(
    client: Any,
    messages: list[dict[str, Any]],
    model: str,
    tools: list[dict[str, Any]] | None = None,
    on_chunk: StreamCallback | None = None,
) -> LLMResponse:
    """Stream an OpenAI-compatible chat completion and return the full response.

    Calls on_chunk(text) for each content delta so callers can display
    incremental output (e.g., SSE to channels, terminal printing).
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        kwargs["tools"] = tools

    content_parts: list[str] = []
    tool_calls_by_idx: dict[int, dict[str, str]] = {}

    stream = await client.chat.completions.create(**kwargs)

    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue

        # Content streaming
        if delta.content:
            content_parts.append(delta.content)
            if on_chunk:
                try:
                    result = on_chunk(delta.content)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass

        # Tool call streaming
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_by_idx:
                    tool_calls_by_idx[idx] = {"id": "", "name": "", "arguments": ""}
                if tc.id:
                    tool_calls_by_idx[idx]["id"] = tc.id
                if tc.function and tc.function.name:
                    tool_calls_by_idx[idx]["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    tool_calls_by_idx[idx]["arguments"] += tc.function.arguments

    # Build response
    content = "".join(content_parts)
    tool_calls = []
    for idx in sorted(tool_calls_by_idx):
        tc_data = tool_calls_by_idx[idx]
        tool_calls.append(
            ToolCall(
                id=tc_data["id"],
                function={"name": tc_data["name"], "arguments": tc_data["arguments"]},
            )
        )

    return LLMResponse(
        content=content,
        tool_calls=tool_calls if tool_calls else None,
        usage=None,  # Usage not available in streaming mode for most providers
        finish_reason="tool_calls" if tool_calls else "stop",
    )


async def stream_anthropic_response(
    client: Any,
    system: str,
    messages: list[dict[str, Any]],
    model: str,
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    on_chunk: StreamCallback | None = None,
) -> LLMResponse:
    """Stream an Anthropic chat completion and return the full response."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    content_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    current_tool: dict[str, str] | None = None
    input_tokens = 0
    output_tokens = 0

    async with client.messages.stream(**kwargs) as stream:
        async for event in stream:
            if event.type == "content_block_start":
                block = event.content_block
                if hasattr(block, "type"):
                    if block.type == "tool_use":
                        current_tool = {"id": block.id, "name": block.name, "input": ""}
            elif event.type == "content_block_delta":
                delta = event.delta
                if hasattr(delta, "text"):
                    content_parts.append(delta.text)
                    if on_chunk:
                        try:
                            result = on_chunk(delta.text)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception:
                            pass
                elif hasattr(delta, "partial_json") and current_tool is not None:
                    current_tool["input"] += delta.partial_json
            elif event.type == "content_block_stop":
                if current_tool is not None:
                    tool_calls.append(
                        ToolCall(
                            id=current_tool["id"],
                            function={"name": current_tool["name"], "arguments": current_tool["input"]},
                        )
                    )
                    current_tool = None
            elif event.type == "message_delta":
                if hasattr(event, "usage"):
                    output_tokens = getattr(event.usage, "output_tokens", 0)
            elif event.type == "message_start":
                if hasattr(event, "message") and hasattr(event.message, "usage"):
                    input_tokens = getattr(event.message.usage, "input_tokens", 0)

    content = "".join(content_parts)
    usage = UsageInfo(prompt_tokens=input_tokens, completion_tokens=output_tokens)

    return LLMResponse(
        content=content,
        tool_calls=tool_calls if tool_calls else None,
        usage=usage,
        finish_reason="tool_use" if tool_calls else "end_turn",
    )
