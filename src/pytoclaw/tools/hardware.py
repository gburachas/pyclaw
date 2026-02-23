"""Hardware tools — I2C and SPI interfaces (Linux only)."""

from __future__ import annotations

import logging
import os
import struct
import sys
from glob import glob
from typing import Any

from pytoclaw.models import ToolResult
from pytoclaw.protocols import Tool

logger = logging.getLogger(__name__)


class I2CTool(Tool):
    """Interact with I2C devices on Linux."""

    def name(self) -> str:
        return "i2c"

    def description(self) -> str:
        return (
            "Interact with I2C hardware devices. "
            "Supports detecting buses, scanning for devices, reading and writing data. "
            "Linux only."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["detect", "scan", "read", "write"],
                    "description": "Action to perform",
                },
                "bus": {"type": "string", "description": "I2C bus number (e.g., '1')"},
                "address": {
                    "type": "integer",
                    "description": "7-bit I2C device address (0x03-0x77)",
                },
                "register": {
                    "type": "integer",
                    "description": "Register address to read from or write to",
                },
                "data": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Bytes to write",
                },
                "length": {
                    "type": "integer",
                    "description": "Number of bytes to read (1-256, default 1)",
                    "default": 1,
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true for write operations",
                },
            },
            "required": ["action"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        if sys.platform != "linux":
            return ToolResult.error("I2C is only supported on Linux")

        action = args.get("action", "")

        if action == "detect":
            return self._detect()
        elif action == "scan":
            return self._scan(args)
        elif action == "read":
            return self._read(args)
        elif action == "write":
            return self._write(args)
        else:
            return ToolResult.error(f"Unknown action: {action}")

    def _detect(self) -> ToolResult:
        buses = sorted(glob("/dev/i2c-*"))
        if not buses:
            return ToolResult.success("No I2C buses found.")
        return ToolResult.success("Available I2C buses:\n" + "\n".join(buses))

    def _scan(self, args: dict[str, Any]) -> ToolResult:
        bus = args.get("bus", "")
        if not bus:
            return ToolResult.error("Bus number is required")

        dev_path = f"/dev/i2c-{bus}"
        if not os.path.exists(dev_path):
            return ToolResult.error(f"Bus {dev_path} not found")

        try:
            import fcntl

            found = []
            fd = os.open(dev_path, os.O_RDWR)
            try:
                for addr in range(0x03, 0x78):
                    try:
                        fcntl.ioctl(fd, 0x0703, addr)  # I2C_SLAVE
                        # Try reading one byte
                        os.read(fd, 1)
                        found.append(f"0x{addr:02x}")
                    except OSError:
                        pass
            finally:
                os.close(fd)

            if found:
                return ToolResult.success(
                    f"Devices found on bus {bus}: {', '.join(found)}"
                )
            return ToolResult.success(f"No devices found on bus {bus}")
        except Exception as e:
            return ToolResult.error(f"Error scanning bus: {e}")

    def _read(self, args: dict[str, Any]) -> ToolResult:
        bus = args.get("bus", "")
        address = args.get("address", 0)
        register = args.get("register")
        length = min(args.get("length", 1), 256)

        if not bus or not address:
            return ToolResult.error("Bus and address are required")
        if not (0x03 <= address <= 0x77):
            return ToolResult.error("Address must be between 0x03 and 0x77")

        try:
            import fcntl

            dev_path = f"/dev/i2c-{bus}"
            fd = os.open(dev_path, os.O_RDWR)
            try:
                fcntl.ioctl(fd, 0x0703, address)
                if register is not None:
                    os.write(fd, bytes([register]))
                data = os.read(fd, length)
                hex_str = " ".join(f"0x{b:02x}" for b in data)
                return ToolResult.success(f"Read {len(data)} bytes: [{hex_str}]")
            finally:
                os.close(fd)
        except Exception as e:
            return ToolResult.error(f"Error reading I2C: {e}")

    def _write(self, args: dict[str, Any]) -> ToolResult:
        if not args.get("confirm", False):
            return ToolResult.error("Write requires confirm=true for safety")

        bus = args.get("bus", "")
        address = args.get("address", 0)
        register = args.get("register")
        data = args.get("data", [])

        if not bus or not address:
            return ToolResult.error("Bus and address are required")
        if not (0x03 <= address <= 0x77):
            return ToolResult.error("Address must be between 0x03 and 0x77")
        if not data:
            return ToolResult.error("Data is required for write")

        try:
            import fcntl

            dev_path = f"/dev/i2c-{bus}"
            fd = os.open(dev_path, os.O_RDWR)
            try:
                fcntl.ioctl(fd, 0x0703, address)
                payload = bytes(data)
                if register is not None:
                    payload = bytes([register]) + payload
                os.write(fd, payload)
                return ToolResult.success(f"Wrote {len(data)} bytes to 0x{address:02x}")
            finally:
                os.close(fd)
        except Exception as e:
            return ToolResult.error(f"Error writing I2C: {e}")


class SPITool(Tool):
    """Interact with SPI devices on Linux."""

    def name(self) -> str:
        return "spi"

    def description(self) -> str:
        return (
            "Interact with SPI hardware devices. "
            "Supports listing devices, full-duplex transfer, and reading. "
            "Linux only."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "transfer", "read"],
                    "description": "Action to perform",
                },
                "device": {
                    "type": "string",
                    "description": "Device in 'X.Y' format (e.g., '2.0')",
                },
                "speed": {
                    "type": "integer",
                    "description": "Speed in Hz (default 1000000)",
                    "default": 1000000,
                },
                "mode": {
                    "type": "integer",
                    "description": "SPI mode 0-3 (default 0)",
                    "default": 0,
                },
                "bits": {
                    "type": "integer",
                    "description": "Bits per word (default 8)",
                    "default": 8,
                },
                "data": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Bytes to send (transfer only)",
                },
                "length": {
                    "type": "integer",
                    "description": "Bytes to read (read action)",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true for transfer operations",
                },
            },
            "required": ["action"],
        }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        if sys.platform != "linux":
            return ToolResult.error("SPI is only supported on Linux")

        action = args.get("action", "")

        if action == "list":
            devices = sorted(glob("/dev/spidev*"))
            if not devices:
                return ToolResult.success("No SPI devices found.")
            return ToolResult.success("Available SPI devices:\n" + "\n".join(devices))
        elif action == "transfer":
            return self._transfer(args)
        elif action == "read":
            return self._read(args)
        else:
            return ToolResult.error(f"Unknown action: {action}")

    def _transfer(self, args: dict[str, Any]) -> ToolResult:
        if not args.get("confirm", False):
            return ToolResult.error("Transfer requires confirm=true for safety")

        device = args.get("device", "")
        data = args.get("data", [])
        if not device or not data:
            return ToolResult.error("Device and data are required for transfer")

        speed = min(max(args.get("speed", 1000000), 1), 125000000)
        mode = args.get("mode", 0)
        bits = args.get("bits", 8)

        dev_path = f"/dev/spidev{device}"
        if not os.path.exists(dev_path):
            return ToolResult.error(f"Device {dev_path} not found")

        try:
            import fcntl
            import ctypes

            fd = os.open(dev_path, os.O_RDWR)
            try:
                # Set SPI mode, bits, speed
                fcntl.ioctl(fd, 0x6B01, struct.pack("B", mode))  # SPI_IOC_WR_MODE
                fcntl.ioctl(fd, 0x6B03, struct.pack("B", bits))  # SPI_IOC_WR_BITS_PER_WORD
                fcntl.ioctl(fd, 0x40046B04, struct.pack("I", speed))  # SPI_IOC_WR_MAX_SPEED_HZ

                tx = bytes(data)
                rx = bytearray(len(tx))

                # SPI_IOC_MESSAGE ioctl
                spi_ioc_transfer = struct.pack(
                    "QQIIHBBBBH",
                    id(tx),  # tx_buf
                    id(rx),  # rx_buf
                    len(tx),  # len
                    speed,  # speed_hz
                    0,  # delay_usecs
                    bits,  # bits_per_word
                    0,  # cs_change
                    0,  # tx_nbits
                    0,  # rx_nbits
                    0,  # pad
                )
                os.write(fd, tx)
                rx_data = os.read(fd, len(tx))

                hex_str = " ".join(f"0x{b:02x}" for b in rx_data)
                return ToolResult.success(
                    f"Transferred {len(tx)} bytes. Received: [{hex_str}]"
                )
            finally:
                os.close(fd)
        except Exception as e:
            return ToolResult.error(f"SPI transfer error: {e}")

    def _read(self, args: dict[str, Any]) -> ToolResult:
        device = args.get("device", "")
        length = args.get("length", 1)
        if not device:
            return ToolResult.error("Device is required")

        dev_path = f"/dev/spidev{device}"
        if not os.path.exists(dev_path):
            return ToolResult.error(f"Device {dev_path} not found")

        try:
            fd = os.open(dev_path, os.O_RDWR)
            try:
                # Send zeros to clock out data
                os.write(fd, bytes(length))
                data = os.read(fd, length)
                hex_str = " ".join(f"0x{b:02x}" for b in data)
                return ToolResult.success(f"Read {len(data)} bytes: [{hex_str}]")
            finally:
                os.close(fd)
        except Exception as e:
            return ToolResult.error(f"SPI read error: {e}")
