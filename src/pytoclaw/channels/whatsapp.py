"""WhatsApp channel adapter via WebSocket bridge."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class WhatsAppConfig:
    def __init__(self, bridge_url: str = "", allow_from: list[str] | None = None):
        self.bridge_url = bridge_url
        self.allow_from = allow_from or []


class WhatsAppChannel(BaseChannel):
    """WhatsApp channel via WebSocket bridge."""

    def __init__(self, config: WhatsAppConfig, bus: MessageBus):
        super().__init__("whatsapp", config, bus, config.allow_from)
        self._url = config.bridge_url
        self._ws: Any = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        import websockets

        self._ws = await websockets.connect(self._url)
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("WhatsApp channel connected to %s", self._url)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()

    async def send(self, msg: OutboundMessage) -> None:
        if not self._ws:
            return
        payload = json.dumps({"type": "message", "to": msg.chat_id, "content": msg.content})
        await self._ws.send(payload)

    async def _listen(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                    sender = data.get("from", "")
                    chat_id = data.get("chat_id", sender)
                    content = data.get("content", "")
                    metadata = {
                        "message_id": data.get("id", ""),
                        "peer_kind": "direct",
                        "peer_id": chat_id,
                    }
                    await self.handle_message(sender, chat_id, content, metadata=metadata)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from WhatsApp bridge")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("WhatsApp listen error")
