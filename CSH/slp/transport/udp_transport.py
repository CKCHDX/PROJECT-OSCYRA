"""
Async UDP transport for SLP.

Wraps asyncio's DatagramProtocol with queued receive and typed send.
"""

import asyncio
import logging
from typing import Tuple, Optional, Callable, Awaitable

from ..protocol.packet_v2 import SLPPacket, pack, unpack

logger = logging.getLogger(__name__)

Address = Tuple[str, int]

MAX_DATAGRAM = 65507


class _UDPProtocol(asyncio.DatagramProtocol):
    """Low-level asyncio protocol fed into the event loop."""

    def __init__(self, on_message: Callable[[SLPPacket, Address], Awaitable[None]]):
        self._on_message = on_message
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: Address):
        try:
            packet = unpack(data)
        except Exception as exc:
            logger.warning("Malformed datagram from %s: %s", addr, exc)
            return
        asyncio.ensure_future(self._on_message(packet, addr))

    def error_received(self, exc: Exception):
        logger.error("UDP error: %s", exc)


class UDPTransport:
    """High-level async UDP transport for SLP packets."""

    def __init__(self, bind_addr: str = "127.0.0.1", bind_port: int = 14270):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self._protocol: Optional[_UDPProtocol] = None
        self._transport: Optional[asyncio.DatagramTransport] = None

    async def start(self, on_message: Callable[[SLPPacket, Address], Awaitable[None]]):
        """Bind the UDP socket and start receiving."""
        loop = asyncio.get_running_loop()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: _UDPProtocol(on_message),
            local_addr=(self.bind_addr, self.bind_port),
        )
        actual = self._transport.get_extra_info("sockname")
        self.bind_port = actual[1]
        logger.info("UDP transport listening on %s:%d", self.bind_addr, self.bind_port)

    async def send(self, packet: SLPPacket, addr: Address):
        """Serialize and send a packet to *addr*."""
        if self._transport is None:
            raise RuntimeError("Transport not started")
        data = pack(packet)
        if len(data) > MAX_DATAGRAM:
            raise ValueError(f"Datagram too large: {len(data)}")
        self._transport.sendto(data, addr)

    def close(self):
        if self._transport:
            self._transport.close()
            self._transport = None
            logger.info("UDP transport closed")
