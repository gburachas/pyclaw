"""Message tool — sends messages to the user via channel."""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from pyclaw.models import ToolResult
from pyclaw.protocols import ContextualTool


SendCallback = Callable[[str, str, str], Coroutine[Any, Any, None]]


class MessageTool(ContextualTool):
    """Send a message to the user on a specific channel."""

    def __init__(self) -> None:
        self._channel = ""
        self._chat_id = ""
        self._send_callback: SendCallback | None = None

    def name(self) -> str:
        return "message"

    def description(self) -> str:
        return "Send a message to the user. Used for notifications and async task results."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The message content to send"},
            },
            "required": ["content"],
        }

    def set_context(self, channel: str, chat_id: str) -> None:
        self._channel = channel
        self._chat_id = chat_id

    def set_send_callback(self, callback: SendCallback) -> None:
        self._send_callback = callback

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        content = args.get("content", "")
        if not content:
            return ToolResult.error("No content provided")
        if self._send_callback:
            await self._send_callback(self._channel, self._chat_id, content)
            return ToolResult.silent_result("Message sent")
        return ToolResult.error("No send callback configured")


class EchoTool:
    """Simple echo tool that returns its input."""

    def name(self) -> str:
        return "echo"

    def description(self) -> str:
        return "Echo back the provided text. Useful for testing."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo back"},
            },
            "required": ["text"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult.success(args.get("text", ""))
