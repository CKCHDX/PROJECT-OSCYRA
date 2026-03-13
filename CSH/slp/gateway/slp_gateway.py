"""
SLP Gateway — CSH-side SLP endpoint.

Listens on a UDP port (default 14270) and manages encrypted sessions
with all registered services.  Provides an API surface for the rest
of CSH to send commands and query service state.
"""

import asyncio
import json
import logging
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Callable, Awaitable

from ..protocol.packet_v2 import (
    SLPPacket, PacketType, PacketFlag, make_packet, pack, unpack, HEADER_SIZE,
)
from ..protocol.session import SLPSession, SessionState
from ..transport.udp_transport import UDPTransport, Address
from ..encryption.triple_layer import TripleLayerEncryption

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Runtime state for a registered service."""
    service_id: str = ""
    service_name: str = ""
    version: str = ""
    http_port: int = 0
    domain: str = ""
    status: str = "offline"  # offline | healthy | unhealthy
    last_heartbeat: float = 0.0
    metrics: dict = field(default_factory=dict)
    session: Optional[SLPSession] = None
    addr: Optional[Address] = None
    logs: list = field(default_factory=list)


# Default heartbeat timeout (seconds).
HEARTBEAT_TIMEOUT = 30.0
HEARTBEAT_CHECK_INTERVAL = 5.0
# Maximum stored log lines per service.
MAX_LOG_LINES = 500


class SLPGateway:
    """CSH-side SLP gateway managing service sessions."""

    def __init__(
        self,
        bind_addr: str = "127.0.0.1",
        bind_port: int = 14270,
        private_key=None,
        allowed_keys: Optional[Dict[str, bytes]] = None,
    ):
        self._bind_addr = bind_addr
        self._bind_port = bind_port
        self._encryption = TripleLayerEncryption(static_private_key=private_key)
        # service_id → allowed raw public key bytes (32 bytes each).
        self._allowed_keys: Dict[str, bytes] = allowed_keys or {}
        self._transport: Optional[UDPTransport] = None

        # addr → pending TripleLayerEncryption awaiting HANDSHAKE_FIN.
        self._pending_handshakes: Dict[Address, TripleLayerEncryption] = {}
        # session_id → SLPSession (only ESTABLISHED sessions).
        self._sessions: Dict[int, SLPSession] = {}
        # service_id → ServiceInfo.
        self.services: Dict[str, ServiceInfo] = {}

        self._running = False
        self._session_counter = 0

        # Callbacks CSH can set.
        self.on_register: Optional[Callable[[ServiceInfo], Awaitable[None]]] = None
        self.on_heartbeat: Optional[Callable[[str, dict], Awaitable[None]]] = None
        self.on_log: Optional[Callable[[str, dict], Awaitable[None]]] = None
        self.on_status_change: Optional[Callable[[str, str], Awaitable[None]]] = None

    # ── Public API ────────────────────────────────────────────────────

    def get_public_key(self) -> bytes:
        return self._encryption.get_public_key()

    async def start(self):
        self._transport = UDPTransport(self._bind_addr, self._bind_port)
        await self._transport.start(self._handle_packet)
        self._running = True
        asyncio.create_task(self._heartbeat_monitor())
        logger.info("SLP Gateway listening on %s:%d", self._bind_addr, self._bind_port)

    def stop(self):
        self._running = False
        if self._transport:
            self._transport.close()
        logger.info("SLP Gateway stopped")

    async def send_command(self, service_id: str, command: str, **kwargs):
        """Send a COMMAND to a service."""
        info = self.services.get(service_id)
        if not info or not info.session or info.session.state != SessionState.ESTABLISHED:
            logger.warning("Cannot send command to %s: not connected", service_id)
            return
        msg = {"type": "COMMAND", "command": command, **kwargs}
        await self._send_encrypted(info.session, PacketType.COMMAND, msg, info.addr)

    # ── Packet handler ────────────────────────────────────────────────

    async def _handle_packet(self, packet: SLPPacket, addr: Address):
        pt = packet.packet_type
        if pt == PacketType.HANDSHAKE_INIT:
            await self._handle_handshake_init(packet, addr)
        elif pt == PacketType.HANDSHAKE_FIN:
            await self._handle_handshake_fin(packet, addr)
        elif pt in (PacketType.HEARTBEAT, PacketType.LOG_ENTRY,
                     PacketType.COMMAND_ACK, PacketType.DATA):
            await self._handle_session_packet(packet, addr)
        elif pt == PacketType.CLOSE:
            self._close_session(packet.session_id)

    # ── Handshake ─────────────────────────────────────────────────────

    async def _handle_handshake_init(self, packet: SLPPacket, addr: Address):
        enc = TripleLayerEncryption(static_private_key=self._encryption.noise.static_private)
        try:
            response_payload = enc.respond_handshake(packet.payload)
        except Exception as exc:
            logger.error("Handshake INIT failed from %s: %s", addr, exc)
            return

        self._session_counter += 1
        session_id = self._session_counter & 0xFFFFFFFF
        self._pending_handshakes[addr] = enc

        resp = make_packet(
            PacketType.HANDSHAKE_RESP, response_payload,
            session_id=session_id, sequence=0,
        )
        await self._transport.send(resp, addr)
        logger.debug("HANDSHAKE_RESP sent to %s (session 0x%08X)", addr, session_id)

    async def _handle_handshake_fin(self, packet: SLPPacket, addr: Address):
        enc = self._pending_handshakes.pop(addr, None)
        if enc is None:
            logger.warning("Unexpected HANDSHAKE_FIN from %s", addr)
            return

        session_id = packet.session_id
        seq = packet.sequence
        session = SLPSession(session_id)
        session.encryption = enc
        session.remote_addr = addr

        # Decrypt the REGISTER payload.
        try:
            header_aad = self._make_header_aad(session_id, seq)
            plaintext = enc.decrypt(packet.payload, counter=seq, aad=header_aad)
            msg = json.loads(plaintext)
        except Exception as exc:
            logger.error("HANDSHAKE_FIN decrypt failed: %s", exc)
            return

        if msg.get("type") != "REGISTER":
            logger.error("Expected REGISTER in HANDSHAKE_FIN, got %s", msg.get("type"))
            return

        service_id = msg.get("service_id", "")

        # Public-key verification.
        if self._allowed_keys:
            from cryptography.hazmat.primitives import serialization as _ser
            remote_pub = enc.noise.remote_static_public
            if remote_pub is None:
                logger.error("No remote public key for %s", service_id)
                return
            remote_bytes = remote_pub.public_bytes(
                encoding=_ser.Encoding.Raw, format=_ser.PublicFormat.Raw,
            )
            expected = self._allowed_keys.get(service_id)
            if expected and remote_bytes != expected:
                logger.error("Public key mismatch for %s — rejecting", service_id)
                return

        session.accept_sequence(seq)
        session.mark_established()
        self._sessions[session_id] = session

        info = ServiceInfo(
            service_id=service_id,
            service_name=msg.get("service_name", ""),
            version=msg.get("version", ""),
            http_port=msg.get("http_port", 0),
            domain=msg.get("metadata", {}).get("domain", ""),
            status="healthy",
            last_heartbeat=time.time(),
            session=session,
            addr=addr,
        )
        self.services[service_id] = info
        logger.info("Service registered: %s (session 0x%08X)", service_id, session_id)

        # Send REGISTER_ACK.
        ack = {"type": "REGISTER_ACK", "status": "ok"}
        await self._send_encrypted(session, PacketType.DATA, ack, addr)

        if self.on_register:
            await self.on_register(info)

    # ── Session packets ───────────────────────────────────────────────

    async def _handle_session_packet(self, packet: SLPPacket, addr: Address):
        session = self._sessions.get(packet.session_id)
        if not session or session.state != SessionState.ESTABLISHED:
            return
        seq = packet.sequence
        if not session.accept_sequence(seq):
            return
        try:
            header_aad = self._make_header_aad(session.session_id, seq)
            plaintext = session.encryption.decrypt(packet.payload, counter=seq, aad=header_aad)
            msg = json.loads(plaintext)
        except Exception:
            return

        msg_type = msg.get("type", "")
        service_id = msg.get("service_id", "")
        info = self.services.get(service_id)

        if msg_type == "HEARTBEAT" and info:
            info.last_heartbeat = time.time()
            info.status = msg.get("status", "healthy")
            info.metrics = msg.get("metrics", {})
            # Send ACK.
            ack = {"type": "HEARTBEAT_ACK", "timestamp": time.time()}
            await self._send_encrypted(session, PacketType.HEARTBEAT_ACK, ack, addr)
            if self.on_heartbeat:
                await self.on_heartbeat(service_id, info.metrics)

        elif msg_type == "LOG_ENTRY" and info:
            info.logs.append(msg)
            if len(info.logs) > MAX_LOG_LINES:
                info.logs = info.logs[-MAX_LOG_LINES:]
            if self.on_log:
                await self.on_log(service_id, msg)

        elif msg_type == "COMMAND_ACK":
            logger.debug("COMMAND_ACK from %s: %s", service_id, msg.get("command"))

    # ── Heartbeat monitor ─────────────────────────────────────────────

    async def _heartbeat_monitor(self):
        while self._running:
            now = time.time()
            for sid, info in list(self.services.items()):
                if info.status == "offline":
                    continue
                if info.last_heartbeat and (now - info.last_heartbeat) > HEARTBEAT_TIMEOUT:
                    old = info.status
                    info.status = "unhealthy"
                    logger.warning("Service %s heartbeat timeout", sid)
                    if self.on_status_change and old != "unhealthy":
                        await self.on_status_change(sid, "unhealthy")
            await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)

    # ── Session teardown ──────────────────────────────────────────────

    def _close_session(self, session_id: int):
        session = self._sessions.pop(session_id, None)
        if session:
            session.mark_closed()
        for sid, info in self.services.items():
            if info.session and info.session.session_id == session_id:
                info.status = "offline"
                info.session = None
                logger.info("Service %s disconnected", sid)
                break

    # ── Helpers ────────────────────────────────────────────────────────

    async def _send_encrypted(self, session: SLPSession, pkt_type: int, msg: dict, addr: Address):
        payload = json.dumps(msg).encode()
        seq = session.next_sequence()
        header_aad = self._make_header_aad(session.session_id, seq)
        enc = session.encryption.encrypt(payload, counter=seq, aad=header_aad)
        pkt = make_packet(pkt_type, enc, session_id=session.session_id, sequence=seq, flags=PacketFlag.ENCRYPTED)
        await self._transport.send(pkt, addr)

    @staticmethod
    def _make_header_aad(session_id: int, seq: int) -> bytes:
        return struct.pack("!IQ", session_id, seq)
