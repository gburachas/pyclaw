"""Feishu (Lark) channel adapter."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class FeishuChannel(BaseChannel):
    """Feishu/Lark bot channel via WebSocket SDK."""

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__("feishu", config, bus, getattr(config, "allow_from", []))
        self._app_id = getattr(config, "app_id", "")
        self._app_secret = getattr(config, "app_secret", "")
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        # Feishu Lark SDK integration
        self._running = True
        logger.info("Feishu channel started (app_id: %s...)", self._app_id[:8] if self._app_id else "?")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def send(self, msg: OutboundMessage) -> None:
        logger.info("Feishu send to %s: %s", msg.chat_id, msg.content[:50])
