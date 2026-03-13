#!/usr/bin/env python3
"""
SLP Simple Server - Proof of Concept

Basic UDP server for testing SLP protocol.
No encryption - just validates core communication.

Usage:
    python examples/server.py
"""

import socket
import sys
from datetime import datetime

HOST = '0.0.0.0'
PORT = 4270
BUFFER_SIZE = 4096


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")


def create_html_response(content):
    """Create basic HTML response."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SLP Test Server</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #0a0a0a;
                color: #00e5ff;
            }}
            h1 {{
                border-bottom: 2px solid #00e5ff;
                padding-bottom: 10px;
            }}
            .success {{
                background: rgba(0, 229, 255, 0.1);
                border-left: 4px solid #00e5ff;
                padding: 15px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h1>🚀 SLP Server Active</h1>
        <div class="success">
            <h2>Connection Successful!</h2>
            <p><strong>Message received:</strong> {content}</p>
            <p><strong>Protocol:</strong> SLP (Secure Line Protocol)</p>
            <p><strong>Transport:</strong> UDP</p>
            <p><strong>Encryption:</strong> None (Testing Phase)</p>
        </div>
        <p>Server is running on {HOST}:{PORT}</p>
    </body>
    </html>
    """
    return html


def main():
    """Main server loop."""
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        
        log(f"✅ SLP Server started")
        log(f"🔊 Listening on {HOST}:{PORT}")
        log(f"📦 Buffer size: {BUFFER_SIZE} bytes")
        log("")
        log("Waiting for connections...")
        log("Press Ctrl+C to stop")
        log("="*50)
        
        while True:
            # Receive data
            data, addr = sock.recvfrom(BUFFER_SIZE)
            client_ip, client_port = addr
            
            log(f"📨 Request from {client_ip}:{client_port}")
            log(f"   Size: {len(data)} bytes")
            
            # Decode message
            try:
                message = data.decode('utf-8')
                log(f"   Data: {message[:100]}..." if len(message) > 100 else f"   Data: {message}")
            except:
                log(f"   Data: [Binary, {len(data)} bytes]")
                message = "[Binary data]"
            
            # Create HTML response
            html_content = create_html_response(message)
            
            # Create HTTP-like response
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            ) + html_content.encode('utf-8')
            
            # Send response
            sock.sendto(response, addr)
            log(f"✅ Response sent ({len(response)} bytes)")
            log("="*50)
    
    except KeyboardInterrupt:
        log("")
        log("⚠️  Server shutdown requested")
    except Exception as e:
        log(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        sock.close()
        log("🚫 Server stopped")


if __name__ == "__main__":
    main()
