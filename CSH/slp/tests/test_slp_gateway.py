"""Unit tests for slp.gateway.slp_gateway."""

import struct
import json
import pytest

from slp.gateway.slp_gateway import SLPGateway, ServiceInfo, HEARTBEAT_TIMEOUT
from slp.protocol.packet_v2 import PacketType, PacketFlag, make_packet
from slp.protocol.session import SessionState


class TestServiceInfo:
    def test_default_values(self):
        info = ServiceInfo()
        assert info.service_id == ""
        assert info.status == "offline"
        assert info.metrics == {}
        assert info.logs == []
        assert info.session is None

    def test_custom_values(self):
        info = ServiceInfo(
            service_id="klar-001",
            service_name="Klar",
            http_port=4271,
            status="healthy",
        )
        assert info.service_id == "klar-001"
        assert info.service_name == "Klar"
        assert info.http_port == 4271


class TestSLPGatewayInit:
    def test_default_bind(self):
        gw = SLPGateway()
        assert gw._bind_addr == "127.0.0.1"
        assert gw._bind_port == 14270

    def test_custom_bind(self):
        gw = SLPGateway(bind_addr="127.0.0.1", bind_port=15000)
        assert gw._bind_port == 15000

    def test_allowed_keys(self):
        keys = {"svc-1": b"\x00" * 32}
        gw = SLPGateway(allowed_keys=keys)
        assert gw._allowed_keys == keys

    def test_public_key_is_32_bytes(self):
        gw = SLPGateway()
        assert len(gw.get_public_key()) == 32


class TestCloseSession:
    def test_close_unknown_session(self):
        gw = SLPGateway()
        # Should not raise.
        gw._close_session(999)

    def test_close_marks_offline(self):
        from slp.protocol.session import SLPSession
        gw = SLPGateway()
        session = SLPSession(1)
        session.mark_established()
        gw._sessions[1] = session
        info = ServiceInfo(service_id="test", session=session, status="healthy")
        gw.services["test"] = info
        gw._close_session(1)
        assert info.status == "offline"
        assert info.session is None
        assert 1 not in gw._sessions


class TestMakeHeaderAad:
    def test_aad_format(self):
        aad = SLPGateway._make_header_aad(42, 99)
        sid, seq = struct.unpack("!IQ", aad)
        assert sid == 42
        assert seq == 99
        assert len(aad) == 12
