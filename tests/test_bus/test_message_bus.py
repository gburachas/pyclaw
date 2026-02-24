"""Tests for message bus."""

import pytest

from pyclaw.bus.message_bus import MessageBus
from pyclaw.models import InboundMessage, OutboundMessage


@pytest.mark.asyncio
async def test_inbound_pub_sub():
    bus = MessageBus()
    msg = InboundMessage(channel="test", content="hello")
    await bus.publish_inbound(msg)
    received = await bus.consume_inbound()
    assert received is not None
    assert received.content == "hello"


@pytest.mark.asyncio
async def test_outbound_pub_sub():
    bus = MessageBus()
    msg = OutboundMessage(channel="test", content="response")
    await bus.publish_outbound(msg)
    received = await bus.consume_outbound()
    assert received is not None
    assert received.content == "response"


@pytest.mark.asyncio
async def test_consume_timeout():
    bus = MessageBus()
    received = await bus.consume_inbound()
    assert received is None


@pytest.mark.asyncio
async def test_close():
    bus = MessageBus()
    bus.close()
    received = await bus.consume_inbound()
    assert received is None
