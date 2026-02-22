"""Tests for core data models."""

from pytoclaw.models import (
    FunctionCall,
    InboundMessage,
    LLMResponse,
    Message,
    Session,
    ToolCall,
    ToolResult,
)


def test_message_creation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.tool_calls == []


def test_tool_call():
    tc = ToolCall(
        id="call_1",
        function=FunctionCall(name="read_file", arguments='{"path": "test.txt"}'),
    )
    assert tc.function.name == "read_file"


def test_tool_result_constructors():
    assert ToolResult.success("ok").for_llm == "ok"
    assert ToolResult.error("bad").is_error is True
    assert ToolResult.silent_result("shhh").silent is True
    assert ToolResult.async_result("later").is_async is True


def test_llm_response():
    resp = LLMResponse(content="Hello!", finish_reason="stop")
    assert resp.content == "Hello!"
    assert resp.tool_calls == []


def test_inbound_message():
    msg = InboundMessage(channel="telegram", sender_id="123", content="hi")
    assert msg.channel == "telegram"


def test_session_default():
    session = Session(key="test")
    assert session.messages == []
    assert session.summary == ""
