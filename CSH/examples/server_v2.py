#!/usr/bin/env python3
"""
SLP Server v2 - With Packet Support

Enhanced server that uses SLP packet format.
Serves HTML from frontend/test.html.
"""

import socket
import sys
from pathlib import Path
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from slp.protocol.packet import SLPPacket

HOST = '0.0.0.0'
PORT = 4270
BUFFER_SIZE = 65536


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")


def load_html():
    """Load HTML frontend file."""
    html_path = Path(__file__).parent.parent / 'frontend' / 'test.html'
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        log(f"⚠️  Warning: {html_path} not found")
        return """
        <!DOCTYPE html>
        <html>
        <head><title>SLP Server</title></head>
        <body style="font-family: Arial; padding: 2rem; background: #0a0a0a; color: #00e5ff;">
            <h1>✅ SLP Server Running</h1>
            <p>Server is active but test.html is missing.</p>
            <p>Expected location: frontend/test.html</p>
        </body>
        </html>
        """


def create_http_response(html_content: str) -> str:
    """Create HTTP response with HTML content."""
    return (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(html_content.encode('utf-8'))}\r\n"
        "Connection: close\r\n"
        "\r\n"
        + html_content
    )


def main():
    """Main server loop."""
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        
        log("✅ SLP Server v2 started")
        log(f"🔊 Listening on {HOST}:{PORT}")
        log(f"📦 Buffer size: {BUFFER_SIZE} bytes")
        log(f"📝 Protocol: SLP with packet format")
        
        # Load HTML content
        html_content = load_html()
        log(f"🌐 HTML content loaded: {len(html_content)} bytes")
        log("")
        log("Waiting for connections...")
        log("Press Ctrl+C to stop")
        log("="*60)
        
        while True:
            # Receive data
            data, addr = sock.recvfrom(BUFFER_SIZE)
            client_ip, client_port = addr
            
            log(f"📨 Connection from {client_ip}:{client_port}")
            log(f"   Received: {len(data)} bytes")
            
            try:
                # Parse SLP packet
                request_packet = SLPPacket.unpack(data)
                log(f"   Packet: {request_packet}")
                
                # Decode request
                request_data = request_packet.payload.decode('utf-8', errors='replace')
                log(f"   Request: {request_data[:80]}..." if len(request_data) > 80 else f"   Request: {request_data}")
                
                # Create HTTP response
                http_response = create_http_response(html_content)
                
                # Wrap in SLP packet
                response_packet = SLPPacket(
                    SLPPacket.TYPE_RESPONSE,
                    http_response.encode('utf-8')
                )
                
                # Send response
                response_data = response_packet.pack()
                sock.sendto(response_data, addr)
                
                log(f"✅ Response sent: {len(response_data)} bytes")
                
            except ValueError as e:
                log(f"❌ Packet parsing error: {e}")
                # Send error packet
                error_packet = SLPPacket(
                    SLPPacket.TYPE_ERROR,
                    f"Invalid packet: {str(e)}".encode('utf-8')
                )
                sock.sendto(error_packet.pack(), addr)
                
            except Exception as e:
                log(f"❌ Server error: {e}")
                # Send error packet
                error_packet = SLPPacket(
                    SLPPacket.TYPE_ERROR,
                    f"Server error: {str(e)}".encode('utf-8')
                )
                sock.sendto(error_packet.pack(), addr)
            
            log("="*60)
    
    except KeyboardInterrupt:
        log("")
        log("⚠️  Server shutdown requested")
    except Exception as e:
        log(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        sock.close()
        log("🚫 Server stopped")


if __name__ == "__main__":
    main()
