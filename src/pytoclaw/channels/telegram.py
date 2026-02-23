"""Telegram channel adapter using python-telegram-bot."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.config.models import TelegramConfig
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """Telegram bot channel using python-telegram-bot."""

    def __init__(self, config: TelegramConfig, bus: MessageBus):
        super().__init__("telegram", config, bus, config.allow_from)
        self._token = config.token
        self._app: Any = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                filters,
            )
        except ImportError:
            raise ImportError(
                "python-telegram-bot is required. Install with: pip install pytoclaw[telegram]"
            )

        self._app = Application.builder().token(self._token).build()

        # Register handlers
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        self._app.add_handler(
            MessageHandler(filters.VOICE | filters.AUDIO, self._on_voice)
        )

        await self._app.initialize()
        await self._app.start()
        self._task = asyncio.create_task(self._poll())
        self._running = True
        logger.info("Telegram channel started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        if self._app:
            await self._app.stop()
            await self._app.shutdown()

    async def send(self, msg: OutboundMessage) -> None:
        if not self._app:
            return
        try:
            chat_id = int(msg.chat_id)
            # Truncate long messages
            content = msg.content
            if len(content) > 4096:
                content = content[:4093] + "..."
            await self._app.bot.send_message(chat_id=chat_id, text=content)
        except Exception:
            logger.exception("Failed to send Telegram message to %s", msg.chat_id)

    async def _poll(self) -> None:
        """Start polling for updates."""
        try:
            from telegram.ext import ApplicationHandlerStop

            updater = self._app.updater
            if updater:
                await updater.start_polling(drop_pending_updates=True)
                while self._running:
                    await asyncio.sleep(1)
                await updater.stop()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Telegram polling error")

    async def _on_message(self, update: Any, context: Any) -> None:
        """Handle incoming text messages."""
        msg = update.effective_message
        if not msg or not msg.text:
            return

        user = update.effective_user
        sender_id = f"{user.id}|{user.username or ''}" if user else "unknown"
        chat_id = str(msg.chat_id)

        metadata = {
            "message_id": str(msg.message_id),
            "peer_kind": "direct" if msg.chat.type == "private" else "group",
            "peer_id": chat_id,
        }
        if user:
            metadata["user_id"] = str(user.id)
            metadata["username"] = user.username or ""
            metadata["first_name"] = user.first_name or ""
        if msg.chat.type != "private":
            metadata["is_group"] = "true"

        await self.handle_message(sender_id, chat_id, msg.text, metadata=metadata)

    async def _on_voice(self, update: Any, context: Any) -> None:
        """Handle voice/audio messages."""
        msg = update.effective_message
        if not msg:
            return

        user = update.effective_user
        sender_id = f"{user.id}|{user.username or ''}" if user else "unknown"
        chat_id = str(msg.chat_id)

        # Download voice file
        voice = msg.voice or msg.audio
        if voice:
            file = await voice.get_file()
            file_path = f"/tmp/tg_voice_{msg.message_id}.ogg"
            await file.download_to_drive(file_path)
            await self.handle_message(
                sender_id, chat_id, "[voice message]", media=[file_path]
            )

    async def _cmd_start(self, update: Any, context: Any) -> None:
        await update.message.reply_text(
            "Hello! I'm pytoclaw, your AI assistant. Send me a message to get started."
        )

    async def _cmd_help(self, update: Any, context: Any) -> None:
        await update.message.reply_text(
            "Available commands:\n"
            "/start - Introduction\n"
            "/help - Show this help\n"
            "\nJust send a message to chat with me!"
        )
