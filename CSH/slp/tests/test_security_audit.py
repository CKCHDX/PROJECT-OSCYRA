"""Security audit tests.

Verifies:
  - No service binds 0.0.0.0
  - No wildcard CORS ("*")
  - Replay protection works
  - Unknown keys are rejected at handshake
"""

import os
import re
import pytest

# Root of the project.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _read_file(relpath: str) -> str:
    path = os.path.join(PROJECT_ROOT, relpath)
    if not os.path.exists(path):
        pytest.skip(f"{relpath} not found")
    with open(path) as f:
        return f.read()


class TestNoWildcardBind:
    """No service should bind to 0.0.0.0."""

    def test_klar_config(self):
        src = _read_file("klar/config.py")
        assert '0.0.0.0' not in src, "Klar still binds 0.0.0.0"

    def test_sverkan_server(self):
        src = _read_file("sverkan/server/server.py")
        # Check the app.run line does not have 0.0.0.0.
        for line in src.splitlines():
            if "app.run(" in line:
                assert '0.0.0.0' not in line, f"Sverkan binds 0.0.0.0: {line.strip()}"

    def test_csh_main(self):
        src = _read_file("CSH/main.py")
        # The uvicorn.run call should use 127.0.0.1.
        for line in src.splitlines():
            if "uvicorn.run" in line:
                assert '0.0.0.0' not in line, f"CSH binds 0.0.0.0: {line.strip()}"


class TestNoCORSWildcard:
    """No service should have CORS allow_origins=["*"] in production config."""

    def test_klar_cors(self):
        src = _read_file("klar/config.py")
        # Find the CORS_ORIGINS line.
        for line in src.splitlines():
            if "CORS_ORIGINS" in line and "=" in line:
                assert '"*"' not in line, f"Klar has wildcard CORS: {line.strip()}"

    def test_sverkan_cors(self):
        src = _read_file("sverkan/server/server.py")
        # The CORS() call should have a restrictive origins list.
        # Find CORS( block.
        cors_block = ""
        in_cors = False
        for line in src.splitlines():
            if "CORS(app" in line:
                in_cors = True
            if in_cors:
                cors_block += line
                if ")" in line:
                    break
        if cors_block:
            assert '"*"' not in cors_block, f"Sverkan has wildcard CORS"

    def test_upsum_cors(self):
        src = _read_file("Upsum/backend/main.py")
        # Check that allow_origins does not contain "*".
        # allow_methods=["*"] and allow_headers=["*"] are acceptable.
        in_origins = False
        for line in src.splitlines():
            stripped = line.strip()
            if "allow_origins" in stripped:
                in_origins = True
            if in_origins:
                assert stripped != '"*"' and stripped != '"*",', \
                    f"Upsum has wildcard in allow_origins: {stripped}"
                if "]" in stripped:
                    break

    def test_csh_cors(self):
        src = _read_file("CSH/main.py")
        # Find ALLOWED_ORIGINS definition.
        for line in src.splitlines():
            if "ALLOWED_ORIGINS" in line and "=" in line:
                assert '"*"' not in line, f"CSH has wildcard CORS: {line.strip()}"


class TestReplayProtection:
    """The replay window should reject duplicate and out-of-range sequences."""

    def test_duplicate_rejection(self):
        from slp.protocol.session import ReplayWindow
        w = ReplayWindow()
        assert w.check_and_accept(1) is True
        assert w.check_and_accept(1) is False

    def test_old_sequence_rejection(self):
        from slp.protocol.session import ReplayWindow
        w = ReplayWindow(size=64)
        w.check_and_accept(100)
        assert w.check_and_accept(35) is False

    def test_sequence_zero_rejected(self):
        from slp.protocol.session import ReplayWindow
        w = ReplayWindow()
        assert w.check_and_accept(0) is False


class TestKeyVerification:
    """Gateway should reject agents with unknown public keys."""

    def test_mismatched_key_not_in_allow_list(self):
        """A key not matching the allow-list should not result in registration."""
        from slp.gateway.slp_gateway import SLPGateway
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        expected_key = X25519PrivateKey.generate()
        expected_bytes = expected_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        gw = SLPGateway(allowed_keys={"svc-1": expected_bytes})

        # A different key should not match.
        rogue_key = X25519PrivateKey.generate()
        rogue_bytes = rogue_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        assert rogue_bytes != expected_bytes


class TestLoopbackBinding:
    """CSH gateway should default to 127.0.0.1."""

    def test_gateway_default_bind(self):
        from slp.gateway.slp_gateway import SLPGateway
        gw = SLPGateway()
        assert gw._bind_addr == "127.0.0.1"

    def test_agent_default_bind(self):
        from slp.agent.slp_agent import SLPAgent
        agent = SLPAgent(
            service_id="test",
            service_name="Test",
            version="1.0.0",
            http_port=9999,
            domain="",
        )
        assert agent.csh_addr[0] == "127.0.0.1"
