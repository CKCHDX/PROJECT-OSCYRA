"""
SLP Agent — Service-side SLP endpoint.

Generic agent that any service can embed. Handles:
  - Handshake with CSH
  - REGISTER on handshake completion
  - HEARTBEAT every 10 seconds with process metrics
  - LOG_ENTRY forwarding
  - COMMAND reception and execution
  - Auto-reconnect on session loss
"""

import asyncio
import json
import logging
import os
import struct
import time
from typing import Optional, Callable, Awaitable

from ..protocol.packet_v2 import (
    SLPPacket, PacketType, PacketFlag, make_packet, pack, unpack, HEADER_SIZE,
)
from ..protocol.session import SLPSession, SessionState
from ..transport.udp_transport import UDPTransport, Address
from ..encryption.triple_layer import TripleLayerEncryption

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SLPAgent:
    """Service-side SLP agent that connects to the CSH gateway."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        version: str,
        http_port: int,
        domain: str,
        csh_addr: tuple = ("127.0.0.1", 14270),
        bind_port: int = 0,
        private_key=None,
        csh_public_key: Optional[bytes] = None,
        heartbeat_interval: float = 10.0,
        on_command: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.service_id = service_id
        self.service_name = service_name
        self.version = version
        self.http_port = http_port
        self.domain = domain
        self.csh_addr = csh_addr
        self._bind_port = bind_port
        self._heartbeat_interval = heartbeat_interval
        self._on_command = on_command
        self._csh_public_key = csh_public_key

        self._encryption = TripleLayerEncryption(static_private_key=private_key)
        self._transport: Optional[UDPTransport] = None
        self._session: Optional[SLPSession] = None
        self._running = False
        self._connected = False
        self._start_time = time.time()
        self._requests_total = 0

    # ── Public API ────────────────────────────────────────────────────

    def get_public_key(self) -> bytes:
        return self._encryption.get_public_key()

    async def start(self):
        self._transport = UDPTransport("127.0.0.1", self._bind_port)
        await self._transport.start(self._handle_packet)
        self._running = True
        asyncio.create_task(self._connect_loop())
        logger.info("SLP Agent started for %s", self.service_id)

    def stop(self):
        self._running = False
        if self._transport:
            self._transport.close()
        logger.info("SLP Agent stopped for %s", self.service_id)

    async def send_log(self, level: str, message: str, source: str = ""):
        if not self._connected or not self._session:
            return
        entry = {
            "type": "LOG_ENTRY",
            "service_id": self.service_id,
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "source": source,
        }
        await self._send_encrypted(PacketType.LOG_ENTRY, entry)

    # ── Connection lifecycle ──────────────────────────────────────────

    async def _connect_loop(self):
        while self._running:
            if not self._connected:
                try:
                    await self._initiate_handshake()
                except Exception as exc:
                    logger.error("Handshake failed: %s", exc)
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(1)

    async def _initiate_handshake(self):
        # Create a fresh encryption context for each handshake attempt.
        self._encryption = TripleLayerEncryption(
            static_private_key=self._encryption.noise.static_private,
        )
        msg1 = self._encryption.initiate_handshake()
        pkt = make_packet(PacketType.HANDSHAKE_INIT, msg1, session_id=0, sequence=0)
        await self._transport.send(pkt, self.csh_addr)
        logger.debug("HANDSHAKE_INIT sent to %s", self.csh_addr)

    # ── Packet handler ────────────────────────────────────────────────

    async def _handle_packet(self, packet: SLPPacket, addr: Address):
        pt = packet.packet_type
        if pt == PacketType.HANDSHAKE_RESP:
            await self._handle_handshake_resp(packet, addr)
        elif pt in (PacketType.COMMAND, PacketType.HEARTBEAT_ACK,
                     PacketType.COMMAND_ACK, PacketType.DATA):
            await self._handle_encrypted(packet, addr)
        elif pt == PacketType.CLOSE:
            self._connected = False
            logger.info("Session closed by CSH")

    async def _handle_handshake_resp(self, packet: SLPPacket, addr: Address):
        try:
            self._encryption.complete_handshake(packet.payload)
        except Exception as exc:
            logger.error("Handshake completion failed: %s", exc)
            return

        # Verify CSH public key if configured.
        if self._csh_public_key:
            from cryptography.hazmat.primitives import serialization
            remote_pub = self._encryption.noise.remote_static_public
            remote_bytes = remote_pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            if remote_bytes != self._csh_public_key:
                logger.error("CSH public key mismatch — aborting handshake")
                return

        session_id = packet.session_id
        self._session = SLPSession(session_id)
        self._session.encryption = self._encryption
        self._session.mark_established()
        self._connected = True

        # Send REGISTER inside HANDSHAKE_FIN.
        reg = {
            "type": "REGISTER",
            "service_id": self.service_id,
            "service_name": self.service_name,
            "version": self.version,
            "http_port": self.http_port,
            "capabilities": [],
            "metadata": {"domain": self.domain},
        }
        payload_bytes = json.dumps(reg).encode()
        seq = self._session.next_sequence()
        header_aad = self._make_header_aad(session_id, seq)
        enc = self._session.encryption.encrypt(payload_bytes, counter=seq, aad=header_aad)
        pkt = make_packet(
            PacketType.HANDSHAKE_FIN, enc,
            session_id=session_id, sequence=seq,
            flags=PacketFlag.ENCRYPTED,
        )
        await self._transport.send(pkt, addr)
        logger.info("Registered as %s (session 0x%08X)", self.service_id, session_id)

        asyncio.create_task(self._heartbeat_loop())

    async def _handle_encrypted(self, packet: SLPPacket, addr: Address):
        if not self._session or self._session.state != SessionState.ESTABLISHED:
            return
        seq = packet.sequence
        if not self._session.accept_sequence(seq):
            return
        try:
            header_aad = self._make_header_aad(self._session.session_id, seq)
            plaintext = self._session.encryption.decrypt(packet.payload, counter=seq, aad=header_aad)
            msg = json.loads(plaintext)
        except Exception:
            return

        msg_type = msg.get("type", "")
        if msg_type == "COMMAND":
            await self._handle_command(msg)
        elif msg_type == "HEARTBEAT_ACK":
            pass
        elif msg_type == "REGISTER_ACK":
            logger.info("REGISTER_ACK received")

    async def _handle_command(self, msg: dict):
        command = msg.get("command", "")
        logger.info("Received command: %s", command)
        if self._on_command:
            await self._on_command(msg)
        ack = {"type": "COMMAND_ACK", "command": command, "status": "ok"}
        await self._send_encrypted(PacketType.COMMAND_ACK, ack)

    # ── Heartbeat ─────────────────────────────────────────────────────

    async def _heartbeat_loop(self):
        while self._running and self._connected:
            try:
                metrics = self._collect_metrics()
                hb = {
                    "type": "HEARTBEAT",
                    "service_id": self.service_id,
                    "timestamp": time.time(),
                    "status": "healthy",
                    "metrics": metrics,
                }
                await self._send_encrypted(PacketType.HEARTBEAT, hb)
            except Exception as exc:
                logger.error("Heartbeat error: %s", exc)
                self._connected = False
                break
            await asyncio.sleep(self._heartbeat_interval)

    def _collect_metrics(self) -> dict:
        metrics = {
            "uptime_seconds": int(time.time() - self._start_time),
            "requests_total": self._requests_total,
        }
        if HAS_PSUTIL:
            proc = psutil.Process(os.getpid())
            metrics["cpu_percent"] = proc.cpu_percent(interval=0)
            metrics["memory_mb"] = round(proc.memory_info().rss / (1024 * 1024), 1)
        return metrics

    # ── Send helper ───────────────────────────────────────────────────

    async def _send_encrypted(self, pkt_type: int, msg: dict):
        if not self._session:
            return
        payload = json.dumps(msg).encode()
        seq = self._session.next_sequence()
        header_aad = self._make_header_aad(self._session.session_id, seq)
        enc = self._session.encryption.encrypt(payload, counter=seq, aad=header_aad)
        pkt = make_packet(
            pkt_type, enc,
            session_id=self._session.session_id, sequence=seq,
            flags=PacketFlag.ENCRYPTED,
        )
        await self._transport.send(pkt, self.csh_addr)

    @staticmethod
    def _make_header_aad(session_id: int, seq: int) -> bytes:
        return struct.pack("!IQ", session_id, seq)
