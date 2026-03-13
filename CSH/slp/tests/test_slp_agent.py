"""Unit tests for slp.agent.slp_agent."""

import struct
import pytest

from slp.agent.slp_agent import SLPAgent
from slp.protocol.session import SLPSession


class TestSLPAgentInit:
    def test_defaults(self):
        agent = SLPAgent(
            service_id="test-001",
            service_name="Test",
            version="1.0.0",
            http_port=4271,
            domain="test.oscyra.solutions",
        )
        assert agent.service_id == "test-001"
        assert agent.service_name == "Test"
        assert agent.csh_addr == ("127.0.0.1", 14270)
        assert agent._connected is False
        assert agent._running is False

    def test_custom_csh_addr(self):
        agent = SLPAgent(
            service_id="svc",
            service_name="Svc",
            version="1.0.0",
            http_port=4272,
            domain="",
            csh_addr=("10.0.0.1", 15000),
        )
        assert agent.csh_addr == ("10.0.0.1", 15000)

    def test_public_key_32_bytes(self):
        agent = SLPAgent(
            service_id="svc",
            service_name="Svc",
            version="1.0.0",
            http_port=4272,
            domain="",
        )
        assert len(agent.get_public_key()) == 32


class TestMakeHeaderAad:
    def test_aad_format(self):
        aad = SLPAgent._make_header_aad(10, 20)
        sid, seq = struct.unpack("!IQ", aad)
        assert sid == 10
        assert seq == 20
        assert len(aad) == 12


class TestMetrics:
    def test_collect_metrics_has_uptime(self):
        agent = SLPAgent(
            service_id="svc",
            service_name="Svc",
            version="1.0.0",
            http_port=4272,
            domain="",
        )
        metrics = agent._collect_metrics()
        assert "uptime_seconds" in metrics
        assert "requests_total" in metrics
        assert isinstance(metrics["uptime_seconds"], int)
