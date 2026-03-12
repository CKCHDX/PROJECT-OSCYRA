#!/usr/bin/env python3
"""
SLP Packet Format

Basic packet structure for Secure Line Protocol (SLP).
Phase 0: No encryption, simple header + payload format.

Packet Structure (8 byte header + payload):
┌─────────────────────┐
│ Version (1 byte)    │ 0x01
├─────────────────────┤
│ Type (1 byte)       │ 0x01=Request, 0x02=Response, 0x03=Error
├─────────────────────┤
│ Flags (1 byte)      │ 0x00=None, 0x01=Encrypted
├─────────────────────┤
│ Reserved (1 byte)   │ 0x00 (for future use)
├─────────────────────┤
│ Length (4 bytes)    │ Payload length (uint32 big-endian)
├─────────────────────┤
│ Payload (N bytes)   │ Actual data
└─────────────────────┘
"""

import struct
from typing import Optional


class SLPPacket:
    """SLP Protocol Packet."""
    
    # Protocol version
    VERSION = 0x01
    
    # Packet types
    TYPE_REQUEST = 0x01
    TYPE_RESPONSE = 0x02
    TYPE_ERROR = 0x03
    
    # Flags
    FLAG_NONE = 0x00
    FLAG_ENCRYPTED = 0x01
    
    # Header format: !BBBBI = Big-endian, 4 unsigned bytes + 1 unsigned int (4 bytes)
    HEADER_FORMAT = '!BBBBI'
    HEADER_SIZE = 8
    
    def __init__(self, packet_type: int, payload: bytes = b'', flags: int = FLAG_NONE):
        """
        Create a new SLP packet.
        
        Args:
            packet_type: Type of packet (REQUEST, RESPONSE, ERROR)
            payload: Packet payload data
            flags: Packet flags (e.g., ENCRYPTED)
        """
        self.version = self.VERSION
        self.type = packet_type
        self.flags = flags
        self.reserved = 0
        self.payload = payload if isinstance(payload, bytes) else payload.encode('utf-8')
    
    def pack(self) -> bytes:
        """
        Pack packet into bytes for transmission.
        
        Returns:
            bytes: Packed packet data
        """
        header = struct.pack(
            self.HEADER_FORMAT,
            self.version,
            self.type,
            self.flags,
            self.reserved,
            len(self.payload)
        )
        return header + self.payload
    
    @staticmethod
    def unpack(data: bytes) -> 'SLPPacket':
        """
        Unpack bytes into an SLP packet.
        
        Args:
            data: Raw packet data
            
        Returns:
            SLPPacket: Parsed packet
            
        Raises:
            ValueError: If packet is malformed
        """
        if len(data) < SLPPacket.HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} bytes (minimum {SLPPacket.HEADER_SIZE})")
        
        # Unpack header
        version, ptype, flags, reserved, length = struct.unpack(
            SLPPacket.HEADER_FORMAT,
            data[:SLPPacket.HEADER_SIZE]
        )
        
        # Validate version
        if version != SLPPacket.VERSION:
            raise ValueError(f"Unsupported protocol version: 0x{version:02x}")
        
        # Extract payload
        payload_start = SLPPacket.HEADER_SIZE
        payload_end = payload_start + length
        
        if len(data) < payload_end:
            raise ValueError(f"Incomplete packet: expected {length} bytes payload, got {len(data) - SLPPacket.HEADER_SIZE}")
        
        payload = data[payload_start:payload_end]
        
        # Create packet
        packet = SLPPacket(ptype, payload, flags)
        packet.reserved = reserved
        return packet
    
    def __repr__(self) -> str:
        type_name = {self.TYPE_REQUEST: 'REQUEST', self.TYPE_RESPONSE: 'RESPONSE', self.TYPE_ERROR: 'ERROR'}.get(self.type, 'UNKNOWN')
        return f"SLPPacket(type={type_name}, flags=0x{self.flags:02x}, payload={len(self.payload)} bytes)"
    
    def __str__(self) -> str:
        return self.__repr__()


if __name__ == "__main__":
    # Test packet creation and packing/unpacking
    print("Testing SLP Packet Format...\n")
    
    # Create request
    request = SLPPacket(SLPPacket.TYPE_REQUEST, b"GET / HTTP/1.1\r\nHost: test\r\n\r\n")
    print(f"Created: {request}")
    
    # Pack
    packed = request.pack()
    print(f"Packed: {len(packed)} bytes")
    print(f"Header: {' '.join(f'{b:02x}' for b in packed[:8])}")
    
    # Unpack
    unpacked = SLPPacket.unpack(packed)
    print(f"Unpacked: {unpacked}")
    print(f"Payload: {unpacked.payload.decode('utf-8')[:50]}...")
    
    print("\n✅ Packet format test passed!")
