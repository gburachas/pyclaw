"""Anthropic Claude provider."""

from __future__ import annotations

import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from pytoclaw.models import (
    FunctionCall,
    LLMResponse,
    Message,
    ToolCall,
    ToolDefinition,
    UsageInfo,
)
from pytoclaw.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude API."""

    def __init__(self, model: str, api_key: str, api_base: str = "", **kwargs: Any):
        super().__init__(model, api_key, api_base, **kwargs)
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if api_base:
            client_kwargs["base_url"] = api_base
        self._client = AsyncAnthropic(**client_kwargs)

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> LLMResponse:
        opts = options or {}
        model = model or self._model

        # Anthropic requires system message separate from messages
        system_prompt, claude_messages = _split_system(messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": opts.get("max_tokens", 8192),
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if tools:
            kwargs["tools"] = [_to_anthropic_tool(t) for t in tools]

        if "temperature" in opts:
            kwargs["temperature"] = opts["temperature"]

        response = await self._client.messages.create(**kwargs)
        return _from_anthropic_response(response)


def _split_system(messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
    """Split system message from conversation messages for Anthropic."""
    system_prompt = ""
    result = []

    for msg in messages:
        if msg.role == "system":
            system_prompt = msg.content
            continue

        if msg.role == "tool":
            result.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }
                ],
            })
        elif msg.role == "assistant" and msg.tool_calls:
            content: list[dict[str, Any]] = []
            if msg.content:
                content.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                name = tc.function.name if tc.function else tc.name
                args = (
                    json.loads(tc.function.arguments)
                    if tc.function
                    else tc.arguments
                )
                content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": name,
                    "input": args,
                })
            result.append({"role": "assistant", "content": content})
        else:
            result.append({"role": msg.role, "content": msg.content})

    return system_prompt, result


def _to_anthropic_tool(tool: ToolDefinition) -> dict[str, Any]:
    """Convert ToolDefinition to Anthropic tool format."""
    return {
        "name": tool.function.name,
        "description": tool.function.description,
        "input_schema": tool.function.parameters,
    }


def _from_anthropic_response(response: Any) -> LLMResponse:
    """Convert Anthropic response to LLMResponse."""
    content = ""
    tool_calls = []

    for block in response.content:
        if block.type == "text":
            content += block.text
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    type="function",
                    function=FunctionCall(
                        name=block.name,
                        arguments=json.dumps(block.input),
                    ),
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                )
            )

    usage = None
    if response.usage:
        usage = UsageInfo(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        finish_reason=response.stop_reason or "",
        usage=usage,
    )
