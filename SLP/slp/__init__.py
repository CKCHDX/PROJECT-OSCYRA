"""
Secure Line Protocol (SLP) Module

Core cryptographic communication protocol.
Handles encryption, transport, and client/server interactions.

Layers:
- Protocol: Packet structure and routing
- Encryption: TLS 1.3, DTLS 1.3, Noise Protocol
- Transport: UDP, connection pooling, reliability
- Gateway: HTTPS <-> SLP conversion for browsers
- Proxy: Local HTTPS proxy for desktop apps
- Client: Client libraries for service communication
"""

__version__ = "1.0.0"
__author__ = "CKCHDX"
__module_name__ = "SLP - Secure Line Protocol"

__all__ = [
    "protocol",
    "encryption",
    "transport",
    "gateway",
    "proxy",
    "client",
    "utils",
]
