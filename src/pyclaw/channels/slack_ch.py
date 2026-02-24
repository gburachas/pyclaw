"""Slack channel adapter using slack-bolt."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pyclaw.bus.message_bus import MessageBus
from pyclaw.channels.base import BaseChannel
from pyclaw.config.models import SlackConfig
from pyclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class SlackChannel(BaseChannel):
    """Slack bot channel using slack-bolt (socket mode)."""

    def __init__(self, config: SlackConfig, bus: MessageBus):
        super().__init__("slack", config, bus, config.allow_from)
        self._bot_token = config.bot_token
        self._app_token = config.app_token
        self._app: Any = None
        self._client: Any = None
        self._bot_user_id = ""
        self._team_id = ""
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            from slack_bolt.async_app import AsyncApp
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
        except ImportError:
            raise ImportError(
                "slack-bolt is required. Install with: pip install pyclaw[slack]"
            )

        self._app = AsyncApp(token=self._bot_token)
        self._client = self._app.client

        # Get bot info
        auth = await self._client.auth_test()
        self._bot_user_id = auth["user_id"]
        self._team_id = auth.get("team_id", "")

        # Register event handlers
        @self._app.event("message")
        async def handle_message(event: dict, say: Any) -> None:
            await self._on_message(event)

        @self._app.event("app_mention")
        async def handle_mention(event: dict, say: Any) -> None:
            await self._on_message(event)

        # Start socket mode
        handler = AsyncSocketModeHandler(self._app, self._app_token)
        self._task = asyncio.create_task(handler.start_async())
        self._running = True
        logger.info("Slack channel started (bot: %s)", self._bot_user_id)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def send(self, msg: OutboundMessage) -> None:
        if not self._client:
            return
        try:
            # chat_id may be "channel_id" or "channel_id/thread_ts"
            parts = msg.chat_id.split("/", 1)
            channel_id = parts[0]
            thread_ts = parts[1] if len(parts) > 1 else None

            kwargs: dict[str, Any] = {
                "channel": channel_id,
                "text": msg.content,
            }
            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            await self._client.chat_postMessage(**kwargs)
        except Exception:
            logger.exception("Failed to send Slack message to %s", msg.chat_id)

    async def _on_message(self, event: dict) -> None:
        """Handle Slack message events."""
        # Ignore bot's own messages
        user_id = event.get("user", "")
        if user_id == self._bot_user_id:
            return

        # Ignore bot messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        text = event.get("text", "")
        channel_id = event.get("channel", "")
        thread_ts = event.get("thread_ts", "")

        # Strip bot mention
        if self._bot_user_id:
            text = text.replace(f"<@{self._bot_user_id}>", "").strip()

        # Use thread-scoped chat_id
        chat_id = f"{channel_id}/{thread_ts}" if thread_ts else channel_id

        metadata = {
            "message_ts": event.get("ts", ""),
            "channel_id": channel_id,
            "platform": "slack",
            "peer_kind": "direct" if event.get("channel_type") == "im" else "group",
            "peer_id": channel_id,
        }
        if thread_ts:
            metadata["thread_ts"] = thread_ts
        if self._team_id:
            metadata["team_id"] = self._team_id

        sender_id = user_id
        await self.handle_message(sender_id, chat_id, text, metadata=metadata)
