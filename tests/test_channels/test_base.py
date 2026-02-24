"""Tests for base channel and channel manager."""

import pytest

from pyclaw.bus.message_bus import MessageBus
from pyclaw.channels.base import BaseChannel, ChannelManager
from pyclaw.models import OutboundMessage


@pytest.fixture
def bus():
    return MessageBus()


class DummyChannel(BaseChannel):
    def __init__(self, name, bus, allow_list=None):
        super().__init__(name, {}, bus, allow_list)
        self.sent: list[OutboundMessage] = []

    async def start(self):
        self._running = True

    async def stop(self):
        self._running = False

    async def send(self, msg):
        self.sent.append(msg)


def test_allow_list_empty(bus):
    ch = DummyChannel("test", bus, [])
    assert ch.is_allowed("anyone") is True


def test_allow_list_match(bus):
    ch = DummyChannel("test", bus, ["123", "456"])
    assert ch.is_allowed("123") is True
    assert ch.is_allowed("789") is False


def test_allow_list_compound(bus):
    ch = DummyChannel("test", bus, ["123"])
    assert ch.is_allowed("123|alice") is True
    assert ch.is_allowed("789|bob") is False


def test_allow_list_at_strip(bus):
    ch = DummyChannel("test", bus, ["@alice"])
    assert ch.is_allowed("alice") is True


@pytest.mark.asyncio
async def test_handle_message_publishes(bus):
    ch = DummyChannel("test", bus, [])
    await ch.handle_message("user1", "chat1", "hello")
    msg = await bus.consume_inbound()
    assert msg is not None
    assert msg.content == "hello"
    assert msg.channel == "test"


@pytest.mark.asyncio
async def test_handle_message_rejected(bus):
    ch = DummyChannel("test", bus, ["allowed_only"])
    await ch.handle_message("not_allowed", "chat1", "hello")
    msg = await bus.consume_inbound()
    assert msg is None


@pytest.mark.asyncio
async def test_channel_manager(bus):
    mgr = ChannelManager(bus)
    ch1 = DummyChannel("ch1", bus)
    ch2 = DummyChannel("ch2", bus)
    mgr.add_channel(ch1)
    mgr.add_channel(ch2)

    await mgr.start_all()
    assert ch1.is_running()
    assert ch2.is_running()
    assert set(mgr.get_enabled_channels()) == {"ch1", "ch2"}

    await mgr.send_to_channel("ch1", "chat1", "hello")
    assert len(ch1.sent) == 1
    assert ch1.sent[0].content == "hello"

    await mgr.stop_all()
    assert not ch1.is_running()
