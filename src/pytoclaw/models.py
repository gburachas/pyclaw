"""Core data models for pytoclaw."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── LLM Messages & Tool Calls ──────────────────────────────────────────────


class FunctionCall(BaseModel):
    name: str
    arguments: str  # JSON string


class ToolCall(BaseModel):
    id: str = ""
    type: str = "function"
    function: FunctionCall | None = None
    name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    role: str  # "system", "user", "assistant", "tool"
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str = ""


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str = ""
    usage: UsageInfo | None = None


# ── Tool Definitions ───────────────────────────────────────────────────────


class ToolFunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    type: str = "function"
    function: ToolFunctionDefinition


class ToolResult(BaseModel):
    for_llm: str = ""
    for_user: str = ""
    silent: bool = False
    is_error: bool = False
    is_async: bool = False

    @classmethod
    def success(cls, content: str) -> ToolResult:
        return cls(for_llm=content)

    @classmethod
    def error(cls, message: str) -> ToolResult:
        return cls(for_llm=message, is_error=True)

    @classmethod
    def silent_result(cls, content: str) -> ToolResult:
        return cls(for_llm=content, silent=True)

    @classmethod
    def async_result(cls, content: str) -> ToolResult:
        return cls(for_llm=content, is_async=True)

    @classmethod
    def user_result(cls, content: str) -> ToolResult:
        return cls(for_user=content)


# ── Bus Messages ───────────────────────────────────────────────────────────


class InboundMessage(BaseModel):
    channel: str = ""
    sender_id: str = ""
    chat_id: str = ""
    content: str = ""
    media: list[str] = Field(default_factory=list)
    session_key: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class OutboundMessage(BaseModel):
    channel: str = ""
    chat_id: str = ""
    content: str = ""


# ── Session ────────────────────────────────────────────────────────────────


class Session(BaseModel):
    key: str
    messages: list[Message] = Field(default_factory=list)
    summary: str = ""
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)


# ── Routing ────────────────────────────────────────────────────────────────


class DMScope(str, Enum):
    MAIN = "main"
    PER_PEER = "per-peer"
    PER_CHANNEL_PEER = "per-channel-peer"
    PER_ACCOUNT_CHANNEL_PEER = "per-account-channel-peer"


class RoutePeer(BaseModel):
    kind: str = ""  # "direct", "group", "channel"
    id: str = ""


class RouteInput(BaseModel):
    channel: str = ""
    account_id: str = ""
    peer: RoutePeer | None = None
    parent_peer: RoutePeer | None = None
    guild_id: str = ""
    team_id: str = ""


class ResolvedRoute(BaseModel):
    agent_id: str = ""
    channel: str = ""
    account_id: str = ""
    session_key: str = ""
    main_session_key: str = ""
    matched_by: str = ""


# ── Failover ───────────────────────────────────────────────────────────────


class FailoverReason(str, Enum):
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    BILLING = "billing"
    TIMEOUT = "timeout"
    FORMAT = "format"
    OVERLOADED = "overloaded"
    UNKNOWN = "unknown"


class FallbackCandidate(BaseModel):
    provider: str = ""
    model: str = ""


class FallbackAttempt(BaseModel):
    provider: str = ""
    model: str = ""
    error: str | None = None
    reason: FailoverReason = FailoverReason.UNKNOWN
    duration_ms: float = 0.0
    skipped: bool = False
