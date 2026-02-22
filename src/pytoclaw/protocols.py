"""Abstract protocols (interfaces) for pytoclaw components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Protocol

from pytoclaw.models import (
    InboundMessage,
    LLMResponse,
    Message,
    OutboundMessage,
    ToolDefinition,
    ToolResult,
)

# ── LLM Provider ──────────────────────────────────────────────────────────


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        model: str,
        options: dict[str, Any] | None = None,
    ) -> LLMResponse:
        ...

    @abstractmethod
    def get_default_model(self) -> str:
        ...


# ── Tool ───────────────────────────────────────────────────────────────────


class Tool(ABC):
    """Base tool interface."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def execute(self, args: dict[str, Any]) -> ToolResult:
        ...


class ContextualTool(Tool):
    """Tool that receives channel/chat context."""

    @abstractmethod
    def set_context(self, channel: str, chat_id: str) -> None:
        ...


AsyncCallback = Callable[[ToolResult], Any]


class AsyncTool(Tool):
    """Tool that supports async callbacks for long-running operations."""

    @abstractmethod
    def set_callback(self, callback: AsyncCallback) -> None:
        ...


# ── Channel ────────────────────────────────────────────────────────────────


class Channel(ABC):
    """Abstract channel interface."""

    @abstractmethod
    def channel_name(self) -> str:
        ...

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        ...

    @abstractmethod
    def is_running(self) -> bool:
        ...

    @abstractmethod
    def is_allowed(self, sender_id: str) -> bool:
        ...


# ── Message Handler ────────────────────────────────────────────────────────


class MessageHandler(Protocol):
    """Protocol for handling inbound messages."""

    def __call__(self, msg: InboundMessage) -> None:
        ...
