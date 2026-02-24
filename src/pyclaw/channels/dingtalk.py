"""DingTalk channel adapter."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pyclaw.bus.message_bus import MessageBus
from pyclaw.channels.base import BaseChannel
from pyclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class DingTalkChannel(BaseChannel):
    """DingTalk bot channel via Stream SDK."""

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__("dingtalk", config, bus, getattr(config, "allow_from", []))
        self._client_id = getattr(config, "client_id", "")
        self._client_secret = getattr(config, "client_secret", "")
        self._session_webhooks: dict[str, str] = {}
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        # DingTalk Stream SDK integration would go here
        # For now, stub that logs readiness
        self._running = True
        logger.info("DingTalk channel started (client_id: %s...)", self._client_id[:8])

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def send(self, msg: OutboundMessage) -> None:
        webhook = self._session_webhooks.get(msg.chat_id)
        if webhook:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(webhook, json={
                    "msgtype": "markdown",
                    "markdown": {"title": "Reply", "text": msg.content},
                })
