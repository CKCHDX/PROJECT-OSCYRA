#!/usr/bin/env python3
"""
SLP Secure Server - With Triple-Layer Encryption

Production-ready server with military-grade security:
- AES-256-GCM encryption
- ChaCha20-Poly1305 encryption
- Noise Protocol (perfect forward secrecy)
"""

import socket
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from slp.protocol.packet import SLPPacket
from slp.encryption.triple_layer import TripleLayerEncryption

HOST = '0.0.0.0'
PORT = 4270
BUFFER_SIZE = 65536

# Store encryption sessions per client
encryption_sessions: Dict[Tuple[str, int], TripleLayerEncryption] = {}


def log(message, level='INFO'):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    icons = {'INFO': '📝', 'SUCCESS': '✅', 'ERROR': '❌', 'WARNING': '⚠️ ', 'SECURITY': '🔒'}
    icon = icons.get(level, '📝')
    print(f"[{timestamp}] {icon} {message}")


def load_html():
    """Load HTML frontend file."""
    html_path = Path(__file__).parent.parent / 'frontend' / 'test.html'
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>✅ SLP Secure Server</h1><p>Frontend not found</p>"


def create_http_response(html_content: str) -> str:
    """Create HTTP response."""
    return (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(html_content.encode('utf-8'))}\r\n"
        "X-Encrypted: SLP-Triple-Layer\r\n"
        "Connection: close\r\n"
        "\r\n"
        + html_content
    )


def main():
    """Main server loop."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        
        log("="*70)
        log("🔒 SLP SECURE SERVER STARTED", 'SUCCESS')
        log("="*70)
        log(f"Listening on {HOST}:{PORT}", 'INFO')
        log(f"Protocol: SLP with Triple-Layer Encryption", 'SECURITY')
        log("")
        log("Security Features:", 'SECURITY')
        log("  ✅ AES-256-GCM (Layer 1)", 'SECURITY')
        log("  ✅ ChaCha20-Poly1305 (Layer 2)", 'SECURITY')
        log("  ✅ Noise Protocol (Layer 3)", 'SECURITY')
        log("  ✅ Perfect Forward Secrecy", 'SECURITY')
        log("  ✅ Authenticated Encryption", 'SECURITY')
        log("="*70)
        
        html_content = load_html()
        log(f"HTML content loaded: {len(html_content)} bytes", 'SUCCESS')
        log("\nWaiting for connections...\n")
        
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            client_key = (addr[0], addr[1])
            
            try:
                # Parse SLP packet
                packet = SLPPacket.unpack(data)
                
                # Check if this is a handshake request
                if packet.type == SLPPacket.TYPE_REQUEST and packet.flags == 0x02:  # Handshake flag
                    log(f"🤝 Handshake request from {addr[0]}:{addr[1]}", 'INFO')
                    
                    # Create new encryption session
                    session = TripleLayerEncryption()
                    
                    # Respond to handshake
                    server_hello = session.respond_handshake(packet.payload)
                    
                    # Store session
                    encryption_sessions[client_key] = session
                    
                    # Send handshake response
                    response_packet = SLPPacket(
                        SLPPacket.TYPE_RESPONSE,
                        server_hello,
                        flags=0x02  # Handshake flag
                    )
                    sock.sendto(response_packet.pack(), addr)
                    
                    log(f"✅ Handshake complete with {addr[0]}:{addr[1]}", 'SUCCESS')
                    log(f"   Perfect forward secrecy: ENABLED", 'SECURITY')
                    continue
                
                # Get encryption session
                session = encryption_sessions.get(client_key)
                
                if not session:
                    log(f"❌ No encryption session for {addr[0]}:{addr[1]}", 'ERROR')
                    error_packet = SLPPacket(
                        SLPPacket.TYPE_ERROR,
                        b"Handshake required"
                    )
                    sock.sendto(error_packet.pack(), addr)
                    continue
                
                # Decrypt request
                log(f"📨 Encrypted request from {addr[0]}:{addr[1]} ({len(data)} bytes)", 'INFO')
                decrypted_payload = session.decrypt(packet.payload, b"SLP-v1.0")
                request = decrypted_payload.decode('utf-8', errors='replace')
                
                log(f"   Decrypted: {request[:60]}...", 'SUCCESS')
                
                # Create HTTP response
                http_response = create_http_response(html_content)
                
                # Encrypt response
                encrypted_payload = session.encrypt(http_response.encode('utf-8'), b"SLP-v1.0")
                
                # Wrap in SLP packet
                response_packet = SLPPacket(
                    SLPPacket.TYPE_RESPONSE,
                    encrypted_payload,
                    flags=0x01  # Encrypted flag
                )
                
                # Send response
                response_data = response_packet.pack()
                sock.sendto(response_data, addr)
                
                log(f"✅ Encrypted response sent: {len(response_data)} bytes", 'SUCCESS')
                log(f"   Overhead: +{len(encrypted_payload) - len(http_response)} bytes (encryption)\n", 'INFO')
                
            except Exception as e:
                log(f"❌ Error: {e}", 'ERROR')
                error_packet = SLPPacket(
                    SLPPacket.TYPE_ERROR,
                    str(e).encode('utf-8')
                )
                sock.sendto(error_packet.pack(), addr)
    
    except KeyboardInterrupt:
        log("\n⚠️  Shutdown requested", 'WARNING')
    except Exception as e:
        log(f"Fatal error: {e}", 'ERROR')
        sys.exit(1)
    finally:
        sock.close()
        log("🚫 Server stopped", 'INFO')


if __name__ == "__main__":
    main()
