"""Device service — USB and hardware event monitoring."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from pyclaw.bus.message_bus import MessageBus

logger = logging.getLogger(__name__)


class DeviceService:
    """Monitors hardware events (USB hotplug on Linux)."""

    def __init__(self, enabled: bool = False, monitor_usb: bool = False):
        self._enabled = enabled
        self._monitor_usb = monitor_usb
        self._bus: MessageBus | None = None
        self._last_channel = ""
        self._last_chat_id = ""
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def set_bus(self, bus: MessageBus) -> None:
        self._bus = bus

    def set_last_channel(self, channel: str, chat_id: str) -> None:
        self._last_channel = channel
        self._last_chat_id = chat_id

    def start(self) -> None:
        if not self._enabled:
            return
        if sys.platform != "linux":
            logger.info("Device monitoring is only supported on Linux")
            return
        self._running = True
        if self._monitor_usb:
            self._task = asyncio.ensure_future(self._monitor_usb_events())
        logger.info("Device service started (USB monitoring: %s)", self._monitor_usb)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _monitor_usb_events(self) -> None:
        """Monitor /dev/bus/usb for changes using polling."""
        known_devices: set[str] = set()

        # Initial scan
        usb_path = Path("/dev/bus/usb")
        if usb_path.exists():
            for dev in usb_path.rglob("*"):
                if dev.is_file():
                    known_devices.add(str(dev))

        while self._running:
            await asyncio.sleep(5)  # Poll every 5 seconds
            if not self._running:
                break

            current_devices: set[str] = set()
            if usb_path.exists():
                for dev in usb_path.rglob("*"):
                    if dev.is_file():
                        current_devices.add(str(dev))

            # Detect new devices
            new_devices = current_devices - known_devices
            removed_devices = known_devices - current_devices

            for dev in new_devices:
                msg = f"USB device connected: {dev}"
                logger.info(msg)
                await self._notify(msg)

            for dev in removed_devices:
                msg = f"USB device disconnected: {dev}"
                logger.info(msg)
                await self._notify(msg)

            known_devices = current_devices

    async def _notify(self, message: str) -> None:
        """Send notification to the last active channel."""
        if self._bus and self._last_channel and self._last_chat_id:
            from pyclaw.models import InboundMessage

            await self._bus.publish_inbound(InboundMessage(
                channel=self._last_channel,
                sender_id="system",
                chat_id=self._last_chat_id,
                content=f"[Device Event] {message}",
                metadata={"source": "device_service"},
            ))
