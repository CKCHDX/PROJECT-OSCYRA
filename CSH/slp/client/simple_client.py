#!/usr/bin/env python3
"""
Simple SLP Client

Basic client for connecting to SLP servers.
Supports custom slp:// URLs and handles packet encoding/decoding.
"""

import socket
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from slp.protocol.packet import SLPPacket


class SimpleSLPClient:
    """Simple SLP protocol client."""
    
    DEFAULT_PORT = 4270
    DEFAULT_TIMEOUT = 5.0
    MAX_RECV_SIZE = 65536  # 64KB
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize SLP client.
        
        Args:
            timeout: Socket timeout in seconds
        """
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
    
    def parse_slp_url(self, url: str) -> Tuple[str, int, str]:
        """
        Parse SLP URL into components.
        
        Args:
            url: SLP URL (e.g., slp://host:port/path)
            
        Returns:
            tuple: (host, port, path)
            
        Raises:
            ValueError: If URL is invalid
        """
        if not url.startswith('slp://'):
            raise ValueError("URL must start with slp://")
        
        # Replace slp:// with http:// for urlparse compatibility
        http_url = url.replace('slp://', 'http://')
        parsed = urlparse(http_url)
        
        host = parsed.hostname or 'localhost'
        port = parsed.port or self.DEFAULT_PORT
        path = parsed.path or '/'
        
        # Add query string if present
        if parsed.query:
            path += '?' + parsed.query
        
        return host, port, path
    
    def connect(self, url: str) -> str:
        """
        Connect to SLP server and retrieve content.
        
        Args:
            url: SLP URL to connect to
            
        Returns:
            str: Response content
            
        Raises:
            Exception: On connection or protocol errors
        """
        host, port, path = self.parse_slp_url(url)
        
        # Create UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.timeout)
        
        try:
            # Create HTTP-style request
            request_data = f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n"
            
            # Wrap in SLP packet
            request_packet = SLPPacket(
                SLPPacket.TYPE_REQUEST,
                request_data.encode('utf-8')
            )
            
            # Send to server
            packed_request = request_packet.pack()
            self.sock.sendto(packed_request, (host, port))
            
            # Receive response
            response_data, addr = self.sock.recvfrom(self.MAX_RECV_SIZE)
            
            # Parse SLP packet
            response_packet = SLPPacket.unpack(response_data)
            
            # Check for errors
            if response_packet.type == SLPPacket.TYPE_ERROR:
                error_msg = response_packet.payload.decode('utf-8', errors='replace')
                raise Exception(f"Server error: {error_msg}")
            
            # Return payload
            return response_packet.payload.decode('utf-8', errors='replace')
            
        except socket.timeout:
            raise Exception(f"Connection timeout: No response from {host}:{port}")
        except Exception as e:
            raise Exception(f"Connection failed: {str(e)}")
        finally:
            self.close()
    
    def close(self):
        """Close socket connection."""
        if self.sock:
            self.sock.close()
            self.sock = None


if __name__ == "__main__":
    # Test client
    import sys
    
    url = sys.argv[1] if len(sys.argv) > 1 else "slp://localhost:4270/"
    
    print(f"Connecting to {url}...")
    
    try:
        client = SimpleSLPClient()
        response = client.connect(url)
        
        print("\nResponse received:")
        print("="*50)
        print(response[:500])  # Print first 500 chars
        if len(response) > 500:
            print(f"\n... ({len(response) - 500} more characters)")
        print("="*50)
        print("\n✅ Connection successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
