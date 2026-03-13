"""
SLP Packet Format v2.

16-byte header for the encrypted SLP protocol.

Header layout (16 bytes, big-endian):
    Byte  0:    packet_type  (uint8)
    Byte  1:    flags        (uint8)
    Bytes 2-5:  session_id   (uint32)
    Bytes 6-13: sequence     (uint64)
    Bytes 14-15: payload_len (uint16)

Protocol version is implicit (v2) and validated by known packet types.
"""

import struct
from typing import NamedTuple

SLP_VERSION = 2
HEADER_FORMAT = "!BBIQH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 16


class PacketType:
    HANDSHAKE_INIT = 0x01
    HANDSHAKE_RESP = 0x02
    HANDSHAKE_FIN  = 0x03
    DATA           = 0x10
    HEARTBEAT      = 0x20
    HEARTBEAT_ACK  = 0x21
    COMMAND        = 0x30
    COMMAND_ACK    = 0x31
    LOG_ENTRY      = 0x40
    REKEY          = 0x50
    CLOSE          = 0xFF

    _NAMES = {
        0x01: "HANDSHAKE_INIT", 0x02: "HANDSHAKE_RESP", 0x03: "HANDSHAKE_FIN",
        0x10: "DATA", 0x20: "HEARTBEAT", 0x21: "HEARTBEAT_ACK",
        0x30: "COMMAND", 0x31: "COMMAND_ACK", 0x40: "LOG_ENTRY",
        0x50: "REKEY", 0xFF: "CLOSE",
    }

    _ALL = set(_NAMES.keys())

    @classmethod
    def name(cls, value: int) -> str:
        return cls._NAMES.get(value, f"UNKNOWN(0x{value:02x})")


class PacketFlag:
    ENCRYPTED  = 0x01
    COMPRESSED = 0x02
    FRAGMENT   = 0x04
    PRIORITY   = 0x08


class SLPPacket(NamedTuple):
    """Immutable SLP v2 packet."""
    packet_type: int
    flags: int
    session_id: int
    sequence: int
    payload: bytes


def make_packet(
    packet_type: int,
    payload: bytes,
    session_id: int = 0,
    sequence: int = 0,
    flags: int = 0,
) -> SLPPacket:
    return SLPPacket(
        packet_type=packet_type,
        flags=flags,
        session_id=session_id,
        sequence=sequence,
        payload=payload,
    )


def pack(packet: SLPPacket) -> bytes:
    """Serialize an SLPPacket to wire bytes."""
    header = struct.pack(
        HEADER_FORMAT,
        packet.packet_type,
        packet.flags,
        packet.session_id,
        packet.sequence,
        len(packet.payload),
    )
    return header + packet.payload


def unpack(data: bytes) -> SLPPacket:
    """Deserialize wire bytes into an SLPPacket."""
    if len(data) < HEADER_SIZE:
        raise ValueError(f"Packet too short: {len(data)} < {HEADER_SIZE}")

    packet_type, flags, session_id, sequence, payload_len = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE],
    )

    expected = HEADER_SIZE + payload_len
    if len(data) < expected:
        raise ValueError(
            f"Incomplete payload: need {payload_len} bytes, got {len(data) - HEADER_SIZE}"
        )

    payload = data[HEADER_SIZE : HEADER_SIZE + payload_len]
    return SLPPacket(packet_type, flags, session_id, sequence, payload)
