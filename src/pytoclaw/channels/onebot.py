"""OneBot channel adapter (QQ via OneBot protocol)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class OneBotChannel(BaseChannel):
    """OneBot v11 channel via WebSocket."""

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__("onebot", config, bus, getattr(config, "allow_from", []))
        self._ws_url = getattr(config, "ws_url", "")
        self._access_token = getattr(config, "access_token", "")
        self._group_trigger_prefix = getattr(config, "group_trigger_prefix", "")
        self._ws: Any = None
        self._task: asyncio.Task | None = None
        self._dedup: deque[str] = deque(maxlen=1024)
        self._self_id = 0

    async def start(self) -> None:
        import websockets

        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        self._ws = await websockets.connect(self._ws_url, extra_headers=headers)
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("OneBot channel connected to %s", self._ws_url)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()

    async def send(self, msg: OutboundMessage) -> None:
        if not self._ws:
            return
        # Parse chat_id format: "private:uid" or "group:gid"
        parts = msg.chat_id.split(":", 1)
        msg_type = parts[0] if len(parts) > 1 else "private"
        target_id = parts[1] if len(parts) > 1 else msg.chat_id

        action = "send_private_msg" if msg_type == "private" else "send_group_msg"
        key = "user_id" if msg_type == "private" else "group_id"

        payload = json.dumps({
            "action": action,
            "params": {key: int(target_id), "message": msg.content},
        })
        await self._ws.send(payload)

    async def _listen(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                    if data.get("post_type") == "message":
                        await self._handle_message(data)
                    elif data.get("post_type") == "meta_event":
                        if data.get("meta_event_type") == "lifecycle":
                            self._self_id = data.get("self_id", 0)
                except json.JSONDecodeError:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("OneBot listen error")

    async def _handle_message(self, data: dict) -> None:
        msg_id = str(data.get("message_id", ""))
        if msg_id in self._dedup:
            return
        self._dedup.append(msg_id)

        user_id = str(data.get("user_id", ""))
        if int(user_id or 0) == self._self_id:
            return

        msg_type = data.get("message_type", "private")
        raw_message = data.get("raw_message", data.get("message", ""))

        if msg_type == "group":
            group_id = str(data.get("group_id", ""))
            chat_id = f"group:{group_id}"
            # Check group trigger
            if self._group_trigger_prefix:
                if not raw_message.startswith(self._group_trigger_prefix):
                    return
                raw_message = raw_message[len(self._group_trigger_prefix):].strip()
        else:
            chat_id = f"private:{user_id}"

        sender = data.get("sender", {})
        metadata = {
            "message_id": msg_id,
            "sender_user_id": user_id,
            "sender_name": sender.get("nickname", ""),
            "peer_kind": "direct" if msg_type == "private" else "group",
            "peer_id": chat_id,
        }

        await self.handle_message(user_id, chat_id, raw_message, metadata=metadata)
