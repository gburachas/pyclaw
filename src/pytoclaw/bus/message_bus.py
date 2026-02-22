"""Async message bus — decouples channels from agent logic."""

from __future__ import annotations

import asyncio
import logging

from pytoclaw.models import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class MessageBus:
    """Async pub/sub message bus using asyncio.Queue."""

    def __init__(self, maxsize: int = 100):
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue(maxsize=maxsize)
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue(maxsize=maxsize)
        self._closed = False

    async def publish_inbound(self, msg: InboundMessage) -> None:
        if not self._closed:
            await self._inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage | None:
        if self._closed:
            return None
        try:
            return await asyncio.wait_for(self._inbound.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        if not self._closed:
            await self._outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage | None:
        if self._closed:
            return None
        try:
            return await asyncio.wait_for(self._outbound.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def close(self) -> None:
        self._closed = True
