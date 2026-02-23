"""Discord channel adapter using discord.py."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.config.models import DiscordConfig
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)

DISCORD_MAX_LENGTH = 2000


class DiscordChannel(BaseChannel):
    """Discord bot channel using discord.py."""

    def __init__(self, config: DiscordConfig, bus: MessageBus):
        super().__init__("discord", config, bus, config.allow_from)
        self._token = config.token
        self._mention_only = config.mention_only
        self._client: Any = None
        self._bot_user_id = ""
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            import discord
        except ImportError:
            raise ImportError(
                "discord.py is required. Install with: pip install pytoclaw[discord]"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready() -> None:
            self._bot_user_id = str(self._client.user.id)
            self._running = True
            logger.info(
                "Discord connected as %s (ID: %s)",
                self._client.user.name,
                self._bot_user_id,
            )

        @self._client.event
        async def on_message(message: Any) -> None:
            await self._on_message(message)

        self._task = asyncio.create_task(self._client.start(self._token))
        # Wait for ready
        for _ in range(30):
            if self._running:
                break
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        if self._client:
            await self._client.close()
        if self._task:
            self._task.cancel()

    async def send(self, msg: OutboundMessage) -> None:
        if not self._client:
            return
        try:
            channel = self._client.get_channel(int(msg.chat_id))
            if channel is None:
                channel = await self._client.fetch_channel(int(msg.chat_id))

            content = msg.content
            # Chunk long messages
            while len(content) > DISCORD_MAX_LENGTH:
                chunk = content[:DISCORD_MAX_LENGTH]
                await channel.send(chunk)
                content = content[DISCORD_MAX_LENGTH:]
            if content:
                await channel.send(content)
        except Exception:
            logger.exception("Failed to send Discord message to %s", msg.chat_id)

    async def _on_message(self, message: Any) -> None:
        """Handle incoming Discord messages."""
        # Ignore own messages
        if message.author.id == self._client.user.id:
            return

        # Mention-only mode
        content = message.content
        is_mention = self._client.user.mentioned_in(message)

        if self._mention_only and not is_mention and not isinstance(
            message.channel, type(None)
        ):
            # Check if it's a DM
            import discord

            if not isinstance(message.channel, discord.DMChannel):
                return

        # Strip bot mention from content
        if is_mention and self._bot_user_id:
            content = content.replace(f"<@{self._bot_user_id}>", "").strip()
            content = content.replace(f"<@!{self._bot_user_id}>", "").strip()

        sender_id = str(message.author.id)
        chat_id = str(message.channel.id)

        import discord as _dc

        is_dm = isinstance(message.channel, _dc.DMChannel)

        metadata = {
            "message_id": str(message.id),
            "user_id": sender_id,
            "username": message.author.name,
            "display_name": message.author.display_name,
            "is_dm": str(is_dm).lower(),
            "peer_kind": "direct" if is_dm else "group",
            "peer_id": chat_id,
        }

        if hasattr(message, "guild") and message.guild:
            metadata["guild_id"] = str(message.guild.id)
            metadata["channel_id"] = chat_id

        await self.handle_message(sender_id, chat_id, content, metadata=metadata)
