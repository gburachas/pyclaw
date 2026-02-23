"""WeCom (WeChat Work) channel adapters — bot and app modes."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class WeComBotChannel(BaseChannel):
    """WeCom bot channel via webhook."""

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__("wecom", config, bus, getattr(config, "allow_from", []))
        self._webhook_url = getattr(config, "webhook_url", "")
        self._token = getattr(config, "token", "")
        self._webhook_host = getattr(config, "webhook_host", "0.0.0.0")
        self._webhook_port = getattr(config, "webhook_port", 8444)
        self._server: Any = None

    async def start(self) -> None:
        self._running = True
        logger.info("WeCom bot channel started")

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(
                self._webhook_url,
                json={"msgtype": "text", "text": {"content": msg.content}},
            )


class WeComAppChannel(BaseChannel):
    """WeCom application channel with token refresh."""

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__("wecom_app", config, bus, getattr(config, "allow_from", []))
        self._corp_id = getattr(config, "corp_id", "")
        self._corp_secret = getattr(config, "corp_secret", "")
        self._agent_id = getattr(config, "agent_id", "")
        self._access_token = ""
        self._token_task: asyncio.Task | None = None

    async def start(self) -> None:
        await self._refresh_token()
        self._token_task = asyncio.create_task(self._token_loop())
        self._running = True
        logger.info("WeCom app channel started (corp: %s)", self._corp_id[:8])

    async def stop(self) -> None:
        self._running = False
        if self._token_task:
            self._token_task.cancel()

    async def send(self, msg: OutboundMessage) -> None:
        import httpx

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self._access_token}"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "touser": msg.chat_id,
                "msgtype": "text",
                "agentid": int(self._agent_id) if self._agent_id else 0,
                "text": {"content": msg.content},
            })

    async def _refresh_token(self) -> None:
        import httpx

        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={
                "corpid": self._corp_id,
                "corpsecret": self._corp_secret,
            })
            data = resp.json()
            self._access_token = data.get("access_token", "")

    async def _token_loop(self) -> None:
        while self._running:
            await asyncio.sleep(300)  # Refresh every 5 minutes
            try:
                await self._refresh_token()
            except Exception:
                logger.exception("WeCom token refresh failed")
