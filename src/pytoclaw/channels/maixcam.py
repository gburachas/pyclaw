"""MaixCAM channel adapter — TCP server for camera AI device."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pytoclaw.bus.message_bus import MessageBus
from pytoclaw.channels.base import BaseChannel
from pytoclaw.models import OutboundMessage

logger = logging.getLogger(__name__)


class MaixCamChannel(BaseChannel):
    """MaixCAM channel via TCP server for device connections."""

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__("maixcam", config, bus, getattr(config, "allow_from", []))
        self._host = getattr(config, "host", "0.0.0.0")
        self._port = getattr(config, "port", 9090)
        self._server: asyncio.Server | None = None
        self._clients: set[asyncio.StreamWriter] = set()

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self._host, self._port
        )
        self._running = True
        logger.info("MaixCAM channel listening on %s:%d", self._host, self._port)

    async def stop(self) -> None:
        self._running = False
        for writer in self._clients:
            writer.close()
        self._clients.clear()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def send(self, msg: OutboundMessage) -> None:
        """Broadcast response to all connected clients."""
        payload = json.dumps({"type": "response", "content": msg.content}).encode() + b"\n"
        dead = set()
        for writer in self._clients:
            try:
                writer.write(payload)
                await writer.drain()
            except Exception:
                dead.add(writer)
        self._clients -= dead

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._clients.add(writer)
        addr = writer.get_extra_info("peername")
        logger.info("MaixCAM client connected: %s", addr)
        try:
            while self._running:
                line = await reader.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode())
                    msg_type = data.get("type", "")
                    if msg_type == "person_detected":
                        content = (
                            f"Person detected: score={data.get('score', 0):.2f} "
                            f"at ({data.get('x', 0)}, {data.get('y', 0)})"
                        )
                        metadata = {
                            "timestamp": str(data.get("timestamp", "")),
                            "class_id": str(data.get("class_id", "")),
                            "score": str(data.get("score", "")),
                            "peer_kind": "direct",
                            "peer_id": "maixcam",
                        }
                        await self.handle_message(
                            "maixcam", "maixcam", content, metadata=metadata
                        )
                    elif msg_type == "heartbeat":
                        pass  # Keepalive
                except json.JSONDecodeError:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("MaixCAM client error")
        finally:
            self._clients.discard(writer)
            writer.close()
