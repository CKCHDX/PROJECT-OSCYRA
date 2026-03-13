"""Unit tests for slp.protocol.packet_v2."""

import struct
import pytest

from slp.protocol.packet_v2 import (
    PacketType, PacketFlag, SLPPacket,
    make_packet, pack, unpack,
    HEADER_SIZE, HEADER_FORMAT, SLP_VERSION,
)


class TestConstants:
    def test_header_size_is_16(self):
        assert HEADER_SIZE == 16

    def test_slp_version(self):
        assert SLP_VERSION == 2

    def test_header_format_size(self):
        assert struct.calcsize(HEADER_FORMAT) == 16


class TestPacketType:
    def test_all_types_defined(self):
        assert PacketType.HANDSHAKE_INIT == 0x01
        assert PacketType.HANDSHAKE_RESP == 0x02
        assert PacketType.HANDSHAKE_FIN == 0x03
        assert PacketType.DATA == 0x10
        assert PacketType.HEARTBEAT == 0x20
        assert PacketType.HEARTBEAT_ACK == 0x21
        assert PacketType.COMMAND == 0x30
        assert PacketType.COMMAND_ACK == 0x31
        assert PacketType.LOG_ENTRY == 0x40
        assert PacketType.REKEY == 0x50
        assert PacketType.CLOSE == 0xFF

    def test_name_lookup(self):
        assert PacketType.name(0x01) == "HANDSHAKE_INIT"
        assert PacketType.name(0xFF) == "CLOSE"
        assert "UNKNOWN" in PacketType.name(0xEE)


class TestPacketFlag:
    def test_flag_values(self):
        assert PacketFlag.ENCRYPTED == 0x01
        assert PacketFlag.COMPRESSED == 0x02
        assert PacketFlag.FRAGMENT == 0x04
        assert PacketFlag.PRIORITY == 0x08

    def test_flags_compose(self):
        combined = PacketFlag.ENCRYPTED | PacketFlag.PRIORITY
        assert combined == 0x09


class TestMakePacket:
    def test_creates_named_tuple(self):
        pkt = make_packet(PacketType.DATA, b"hello")
        assert isinstance(pkt, SLPPacket)
        assert pkt.packet_type == PacketType.DATA
        assert pkt.payload == b"hello"
        assert pkt.session_id == 0
        assert pkt.sequence == 0
        assert pkt.flags == 0

    def test_with_all_fields(self):
        pkt = make_packet(PacketType.HEARTBEAT, b"\x01\x02", session_id=42, sequence=99, flags=0x01)
        assert pkt.session_id == 42
        assert pkt.sequence == 99
        assert pkt.flags == 0x01


class TestPackUnpack:
    def test_roundtrip_empty_payload(self):
        pkt = make_packet(PacketType.CLOSE, b"", session_id=1, sequence=1)
        data = pack(pkt)
        assert len(data) == HEADER_SIZE
        result = unpack(data)
        assert result.packet_type == PacketType.CLOSE
        assert result.payload == b""
        assert result.session_id == 1
        assert result.sequence == 1

    def test_roundtrip_with_payload(self):
        payload = b"encrypted data here"
        pkt = make_packet(PacketType.DATA, payload, session_id=0xDEADBEEF, sequence=12345, flags=PacketFlag.ENCRYPTED)
        data = pack(pkt)
        assert len(data) == HEADER_SIZE + len(payload)
        result = unpack(data)
        assert result.packet_type == PacketType.DATA
        assert result.flags == PacketFlag.ENCRYPTED
        assert result.session_id == 0xDEADBEEF
        assert result.sequence == 12345
        assert result.payload == payload

    def test_roundtrip_large_payload(self):
        payload = os.urandom(8000)
        pkt = make_packet(PacketType.DATA, payload, session_id=7)
        result = unpack(pack(pkt))
        assert result.payload == payload

    def test_unpack_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            unpack(b"\x00" * 10)

    def test_unpack_incomplete_payload(self):
        header = struct.pack(HEADER_FORMAT, 0x10, 0, 0, 0, 100)
        with pytest.raises(ValueError, match="Incomplete"):
            unpack(header + b"\x00" * 50)

    def test_unpack_extra_bytes_ok(self):
        """Extra trailing bytes beyond payload_length are ignored."""
        pkt = make_packet(PacketType.DATA, b"hi")
        data = pack(pkt) + b"\xff\xff\xff"
        result = unpack(data)
        assert result.payload == b"hi"

    def test_max_payload_length(self):
        """Payload length field is uint16, max 65535."""
        payload = b"\x00" * 65535
        pkt = make_packet(PacketType.DATA, payload)
        data = pack(pkt)
        result = unpack(data)
        assert len(result.payload) == 65535

    def test_all_packet_types_roundtrip(self):
        for ptype in PacketType._ALL:
            pkt = make_packet(ptype, b"test", session_id=1, sequence=1)
            result = unpack(pack(pkt))
            assert result.packet_type == ptype


import os  # noqa: E402 - needed for urandom in test_roundtrip_large_payload
