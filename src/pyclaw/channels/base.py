"""Base channel implementation."""

from __future__ import annotations

import logging
from typing import Any

from pyclaw.bus.message_bus import MessageBus
from pyclaw.models import InboundMessage
from pyclaw.protocols import Channel

logger = logging.getLogger(__name__)


class BaseChannel(Channel):
    """Base class for all channel implementations."""

    def __init__(
        self,
        name: str,
        config: Any,
        bus: MessageBus,
        allow_list: list[str] | None = None,
    ):
        self._name = name
        self._config = config
        self._bus = bus
        self._running = False
        self._allow_list = allow_list or []

    def channel_name(self) -> str:
        return self._name

    def is_running(self) -> bool:
        return self._running

    def is_allowed(self, sender_id: str) -> bool:
        """Check if sender is allowed. Empty list = allow all."""
        if not self._allow_list:
            return True
        # Support compound format: "id|username"
        sender_parts = sender_id.split("|")
        for allowed in self._allow_list:
            allowed_clean = allowed.lstrip("@")
            for part in sender_parts:
                if part.lstrip("@") == allowed_clean:
                    return True
        return False

    async def handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Publish an inbound message to the bus."""
        if not self.is_allowed(sender_id):
            logger.debug("Message from %s rejected (not in allow list)", sender_id)
            return

        msg = InboundMessage(
            channel=self._name,
            sender_id=sender_id,
            chat_id=chat_id,
            content=content,
            media=media or [],
            metadata=metadata or {},
        )
        await self._bus.publish_inbound(msg)


class ChannelManager:
    """Manages all channel instances."""

    def __init__(self, bus: MessageBus):
        self._bus = bus
        self._channels: dict[str, Channel] = {}

    def add_channel(self, channel: Channel) -> None:
        self._channels[channel.channel_name()] = channel

    def get_channel(self, name: str) -> Channel | None:
        return self._channels.get(name)

    async def start_all(self) -> None:
        """Start all registered channels."""
        for name, ch in self._channels.items():
            try:
                await ch.start()
                logger.info("Channel %s started", name)
            except Exception:
                logger.exception("Failed to start channel %s", name)

    async def stop_all(self) -> None:
        """Stop all running channels."""
        for name, ch in self._channels.items():
            if ch.is_running():
                try:
                    await ch.stop()
                    logger.info("Channel %s stopped", name)
                except Exception:
                    logger.exception("Failed to stop channel %s", name)

    async def send_to_channel(
        self, channel_name: str, chat_id: str, content: str
    ) -> None:
        """Send a message to a specific channel."""
        from pyclaw.models import OutboundMessage

        ch = self._channels.get(channel_name)
        if ch and ch.is_running():
            await ch.send(OutboundMessage(
                channel=channel_name,
                chat_id=chat_id,
                content=content,
            ))

    def get_enabled_channels(self) -> list[str]:
        return [name for name, ch in self._channels.items() if ch.is_running()]

    def get_status(self) -> dict[str, bool]:
        return {name: ch.is_running() for name, ch in self._channels.items()}
