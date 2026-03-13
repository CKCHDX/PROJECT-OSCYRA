"""Integration tests — full gateway + agent handshake over UDP loopback."""

import asyncio
import json
import pytest

from slp.gateway.slp_gateway import SLPGateway, ServiceInfo
from slp.agent.slp_agent import SLPAgent


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _start_gateway_and_agent(allowed_keys=None, agent_key=None, csh_pub=None):
    """Helper: start a gateway + agent and return them."""
    gw = SLPGateway(bind_addr="127.0.0.1", bind_port=0, allowed_keys=allowed_keys)
    await gw.start()

    gw_port = gw._transport.bind_port

    agent = SLPAgent(
        service_id="integ-001",
        service_name="IntegTest",
        version="1.0.0",
        http_port=9999,
        domain="integ.oscyra.solutions",
        csh_addr=("127.0.0.1", gw_port),
        bind_port=0,
        private_key=agent_key,
        csh_public_key=csh_pub,
        heartbeat_interval=60.0,  # Don't spam during tests.
    )
    return gw, agent


@pytest.mark.asyncio
async def test_full_handshake_and_register():
    """Agent connects, performs handshake, sends REGISTER, gateway acks."""
    gw, agent = await _start_gateway_and_agent()

    registered = asyncio.Event()
    registered_info = {}

    async def on_reg(info: ServiceInfo):
        registered_info.update({
            "service_id": info.service_id,
            "service_name": info.service_name,
        })
        registered.set()

    gw.on_register = on_reg

    await agent.start()

    try:
        await asyncio.wait_for(registered.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pytest.fail("Service registration timed out")

    assert registered_info["service_id"] == "integ-001"
    assert registered_info["service_name"] == "IntegTest"
    assert "integ-001" in gw.services
    assert gw.services["integ-001"].status == "healthy"

    agent.stop()
    gw.stop()


@pytest.mark.asyncio
async def test_heartbeat_received():
    """After registration, heartbeat is received by gateway."""
    gw, agent = await _start_gateway_and_agent()

    hb_received = asyncio.Event()
    hb_data = {}

    async def on_reg(info):
        pass

    async def on_hb(service_id, metrics):
        hb_data["service_id"] = service_id
        hb_data["metrics"] = metrics
        hb_received.set()

    gw.on_register = on_reg
    gw.on_heartbeat = on_hb

    # Use fast heartbeat for testing.
    agent = (await _start_gateway_and_agent())[1]
    gw2, agent = await _start_gateway_and_agent()
    gw2.on_register = on_reg
    gw2.on_heartbeat = on_hb

    # Override heartbeat interval to be fast.
    agent._heartbeat_interval = 0.5

    await agent.start()

    try:
        await asyncio.wait_for(hb_received.wait(), timeout=8.0)
    except asyncio.TimeoutError:
        pytest.fail("Heartbeat not received")

    assert hb_data["service_id"] == "integ-001"
    assert "uptime_seconds" in hb_data["metrics"]

    agent.stop()
    gw2.stop()


@pytest.mark.asyncio
async def test_public_key_verification():
    """Agent with known public key is accepted by gateway."""
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

    agent_priv = X25519PrivateKey.generate()
    from slp.encryption.triple_layer import TripleLayerEncryption
    agent_enc = TripleLayerEncryption(static_private_key=agent_priv)
    agent_pub = agent_enc.get_public_key()

    allowed = {"integ-001": agent_pub}
    gw = SLPGateway(bind_addr="127.0.0.1", bind_port=0, allowed_keys=allowed)
    await gw.start()

    csh_pub = gw.get_public_key()
    gw_port = gw._transport.bind_port

    registered = asyncio.Event()

    async def on_reg(info):
        registered.set()

    gw.on_register = on_reg

    agent = SLPAgent(
        service_id="integ-001",
        service_name="IntegTest",
        version="1.0.0",
        http_port=9999,
        domain="integ.oscyra.solutions",
        csh_addr=("127.0.0.1", gw_port),
        bind_port=0,
        private_key=agent_priv,
        csh_public_key=csh_pub,
        heartbeat_interval=60.0,
    )
    await agent.start()

    try:
        await asyncio.wait_for(registered.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pytest.fail("Registration with key verification timed out")

    assert "integ-001" in gw.services

    agent.stop()
    gw.stop()


@pytest.mark.asyncio
async def test_unknown_key_rejected():
    """Agent with wrong key is rejected by gateway."""
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

    # Gateway expects a specific key.
    expected_pub = X25519PrivateKey.generate().public_key()
    from cryptography.hazmat.primitives import serialization
    expected_bytes = expected_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    allowed = {"integ-001": expected_bytes}
    gw = SLPGateway(bind_addr="127.0.0.1", bind_port=0, allowed_keys=allowed)
    await gw.start()

    gw_port = gw._transport.bind_port

    # Agent uses a DIFFERENT key.
    rogue_key = X25519PrivateKey.generate()
    agent = SLPAgent(
        service_id="integ-001",
        service_name="Rogue",
        version="1.0.0",
        http_port=9999,
        domain="",
        csh_addr=("127.0.0.1", gw_port),
        bind_port=0,
        private_key=rogue_key,
        heartbeat_interval=60.0,
    )
    await agent.start()

    # Wait a bit — the rogue agent should NOT get registered.
    await asyncio.sleep(4)
    assert "integ-001" not in gw.services

    agent.stop()
    gw.stop()
