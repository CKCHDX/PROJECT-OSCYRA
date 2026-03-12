"""
SLP Transport Layer Module

UDP-based transport:
- UDP implementation
- Connection pooling
- Packet fragmentation/reassembly
- Retransmission and reliability
"""

__all__ = [
    "udp_transport",
    "connection_pool",
    "packet_assembler",
    "retransmission",
]
