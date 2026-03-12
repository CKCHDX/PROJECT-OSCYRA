#!/usr/bin/env python3
"""
SLP Connection Test

Automated test to verify SLP server is working.
"""

import socket
import time
import sys

HOST = 'localhost'
PORT = 4270
TIMEOUT = 2.0


def test_connection():
    """Test basic UDP connection."""
    print("Testing SLP connection...")
    print(f"Target: {HOST}:{PORT}")
    print()
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(TIMEOUT)
        
        # Test 1: Send simple message
        print("[1/3] Sending test message...")
        test_msg = b"PING"
        sock.sendto(test_msg, (HOST, PORT))
        
        # Test 2: Receive response
        print("[2/3] Waiting for response...")
        response, addr = sock.recvfrom(4096)
        
        # Test 3: Verify response
        print("[3/3] Verifying response...")
        if len(response) > 0:
            print(f"\n✅ SUCCESS!")
            print(f"   Received {len(response)} bytes")
            print(f"   Server: {addr[0]}:{addr[1]}")
            print(f"\n🎉 SLP server is working!")
            return True
        else:
            print("\n❌ FAILED: Empty response")
            return False
    
    except socket.timeout:
        print("\n❌ FAILED: Connection timeout")
        print("   - Make sure server is running: python examples/server.py")
        print(f"   - Check if port {PORT} is open")
        return False
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False
    finally:
        sock.close()


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
