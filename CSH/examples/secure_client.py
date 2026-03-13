#!/usr/bin/env python3
"""
SLP Secure Client - With Triple-Layer Encryption

Command-line client with full encryption support.
"""

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from slp.protocol.packet import SLPPacket
from slp.encryption.triple_layer import TripleLayerEncryption
from slp.client.simple_client import SimpleSLPClient


class SecureSLPClient:
    """Secure SLP client with triple-layer encryption."""
    
    def __init__(self, timeout=5.0):
        self.timeout = timeout
        self.sock = None
        self.encryption = TripleLayerEncryption()
    
    def connect(self, url: str) -> str:
        """Connect to SLP server with encryption."""
        # Parse URL
        simple_client = SimpleSLPClient()
        host, port, path = simple_client.parse_slp_url(url)
        
        # Create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.timeout)
        
        try:
            # Step 1: Handshake
            print("🔒 Initiating secure handshake...")
            client_hello = self.encryption.initiate_handshake()
            
            handshake_packet = SLPPacket(
                SLPPacket.TYPE_REQUEST,
                client_hello,
                flags=0x02  # Handshake flag
            )
            
            self.sock.sendto(handshake_packet.pack(), (host, port))
            
            # Receive handshake response
            data, addr = self.sock.recvfrom(65536)
            response_packet = SLPPacket.unpack(data)
            
            if response_packet.type == SLPPacket.TYPE_ERROR:
                raise Exception(f"Handshake failed: {response_packet.payload.decode()}")
            
            # Complete handshake
            self.encryption.complete_handshake(response_packet.payload)
            print("✅ Handshake complete")
            print("   ✅ Perfect forward secrecy enabled")
            print("   ✅ Triple-layer encryption active\n")
            
            # Step 2: Send encrypted request
            print("📤 Sending encrypted request...")
            request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n"
            encrypted_request = self.encryption.encrypt(request.encode('utf-8'), b"SLP-v1.0")
            
            request_packet = SLPPacket(
                SLPPacket.TYPE_REQUEST,
                encrypted_request,
                flags=0x01  # Encrypted flag
            )
            
            self.sock.sendto(request_packet.pack(), (host, port))
            
            # Step 3: Receive encrypted response
            print("⏳ Waiting for encrypted response...")
            data, addr = self.sock.recvfrom(65536)
            response_packet = SLPPacket.unpack(data)
            
            if response_packet.type == SLPPacket.TYPE_ERROR:
                raise Exception(f"Server error: {response_packet.payload.decode()}")
            
            # Decrypt response
            print("🔓 Decrypting response...")
            decrypted_response = self.encryption.decrypt(response_packet.payload, b"SLP-v1.0")
            
            print(f"✅ Received {len(decrypted_response)} bytes\n")
            return decrypted_response.decode('utf-8', errors='replace')
            
        except socket.timeout:
            raise Exception(f"Connection timeout: No response from {host}:{port}")
        except Exception as e:
            raise Exception(f"Connection failed: {str(e)}")
        finally:
            if self.sock:
                self.sock.close()


def main():
    """Main client function."""
    url = sys.argv[1] if len(sys.argv) > 1 else "slp://localhost:4270/"
    
    print("="*70)
    print("🔒 SLP SECURE CLIENT")
    print("="*70)
    print(f"Target: {url}")
    print("Security: Triple-Layer Encryption\n")
    
    try:
        client = SecureSLPClient()
        response = client.connect(url)
        
        print("="*70)
        print("📝 RESPONSE:")
        print("="*70)
        print(response[:500])
        if len(response) > 500:
            print(f"\n... ({len(response) - 500} more characters)")
        print("="*70)
        print("✅ Connection successful!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
