"""LINE channel adapter."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class LINEChannel(BaseChannel):
    """LINE bot channel via webhook + REST API."""

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__("line", config, bus, getattr(config, "allow_from", []))
        self._access_token = getattr(config, "channel_access_token", "")
        self._channel_secret = getattr(config, "channel_secret", "")
        self._webhook_host = getattr(config, "webhook_host", "0.0.0.0")
        self._webhook_port = getattr(config, "webhook_port", 8443)
        self._reply_tokens: dict[str, str] = {}
        self._server: Any = None

    async def start(self) -> None:
        from aiohttp import web

        app = web.Application()
        app.router.add_post("/webhook", self._handle_webhook)

        runner = web.AppRunner(app)
        await runner.setup()
        self._server = web.TCPSite(runner, self._webhook_host, self._webhook_port)
        await self._server.start()
        self._running = True
        logger.info("LINE channel started on %s:%d", self._webhook_host, self._webhook_port)

    async def stop(self) -> None:
        self._running = False
        if self._server:
            await self._server.stop()

    async def send(self, msg: OutboundMessage) -> None:
        import httpx

        # Try reply API first, fall back to push API
        reply_token = self._reply_tokens.pop(msg.chat_id, None)
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            if reply_token:
                await client.post(
                    "https://api.line.me/v2/bot/message/reply",
                    headers=headers,
                    json={
                        "replyToken": reply_token,
                        "messages": [{"type": "text", "text": msg.content}],
                    },
                )
            else:
                await client.post(
                    "https://api.line.me/v2/bot/message/push",
                    headers=headers,
                    json={
                        "to": msg.chat_id,
                        "messages": [{"type": "text", "text": msg.content}],
                    },
                )

    async def _handle_webhook(self, request: Any) -> Any:
        from aiohttp import web

        body = await request.read()
        signature = request.headers.get("X-Line-Signature", "")

        # Verify signature
        if self._channel_secret:
            expected = hmac.new(
                self._channel_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return web.Response(status=403)

        import json
        data = json.loads(body)
        for event in data.get("events", []):
            if event.get("type") == "message":
                msg = event.get("message", {})
                source = event.get("source", {})
                sender_id = source.get("userId", "")
                source_type = source.get("type", "user")

                if source_type == "group":
                    chat_id = source.get("groupId", sender_id)
                elif source_type == "room":
                    chat_id = source.get("roomId", sender_id)
                else:
                    chat_id = sender_id

                reply_token = event.get("replyToken", "")
                if reply_token:
                    self._reply_tokens[chat_id] = reply_token

                content = msg.get("text", "")
                metadata = {
                    "message_id": msg.get("id", ""),
                    "source_type": source_type,
                    "platform": "line",
                    "peer_kind": "direct" if source_type == "user" else "group",
                    "peer_id": chat_id,
                }
                await self.handle_message(sender_id, chat_id, content, metadata=metadata)

        return web.Response(text="OK")
