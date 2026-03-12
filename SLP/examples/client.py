#!/usr/bin/env python3
"""
SLP Simple Client - Proof of Concept

Basic UDP client for testing SLP protocol.
No encryption - just validates core communication.

Usage:
    python examples/client.py [host] [port]
    
Examples:
    python examples/client.py
    python examples/client.py localhost 4270
    python examples/client.py 192.168.1.100 4270
"""

import socket
import sys
from datetime import datetime

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 4270
BUFFER_SIZE = 4096
TIMEOUT = 5.0


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")


def send_request(host, port, message):
    """Send request to SLP server and get response."""
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(TIMEOUT)
        
        log(f"🔗 Connecting to {host}:{port}")
        
        # Send request
        request_data = message.encode('utf-8')
        sock.sendto(request_data, (host, port))
        log(f"📤 Sent {len(request_data)} bytes")
        
        # Receive response
        log("⏳ Waiting for response...")
        response_data, addr = sock.recvfrom(BUFFER_SIZE)
        log(f"📥 Received {len(response_data)} bytes from {addr[0]}:{addr[1]}")
        
        # Decode response
        try:
            response = response_data.decode('utf-8')
            log("✅ Response received successfully")
            return response
        except:
            log("⚠️  Response is binary data")
            return response_data
    
    except socket.timeout:
        log("❌ Timeout: No response from server")
        return None
    except ConnectionRefusedError:
        log("❌ Connection refused: Server may not be running")
        return None
    except Exception as e:
        log(f"❌ Error: {e}")
        return None
    finally:
        sock.close()


def main():
    """Main client function."""
    # Parse command line arguments
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            log(f"❌ Invalid port: {sys.argv[2]}")
            sys.exit(1)
    
    # Display info
    log("="*50)
    log("🚀 SLP Simple Client")
    log(f"Target: {host}:{port}")
    log(f"Timeout: {TIMEOUT}s")
    log("="*50)
    log("")
    
    # Create test message
    message = "GET / HTTP/1.1\r\nHost: slp.test\r\n\r\n"
    
    # Send request
    response = send_request(host, port, message)
    
    # Display response
    log("")
    log("="*50)
    if response:
        log("📝 Response:")
        log("="*50)
        if isinstance(response, str):
            # Print first 500 characters
            print(response[:500])
            if len(response) > 500:
                print(f"\n... ({len(response) - 500} more characters)")
        else:
            print(f"Binary data: {len(response)} bytes")
        log("="*50)
        log("✅ Test completed successfully")
    else:
        log("❌ Test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
