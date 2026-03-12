#!/usr/bin/env python3
"""
Test SLP Communication

Test script to verify SLP packet-based communication works.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from slp.client.simple_client import SimpleSLPClient


def test_connection(url="slp://localhost:4270/"):
    """Test SLP connection."""
    print("="*60)
    print("🚀 Testing SLP Connection")
    print("="*60)
    print(f"\nTarget: {url}")
    print("\nConnecting...")
    
    try:
        client = SimpleSLPClient(timeout=5.0)
        response = client.connect(url)
        
        print("\n✅ Connection successful!")
        print(f"\nReceived {len(response)} bytes")
        print("\nFirst 500 characters of response:")
        print("="*60)
        print(response[:500])
        if len(response) > 500:
            print(f"\n... ({len(response) - 500} more characters)")
        print("="*60)
        
        # Check if HTML
        if '<html' in response.lower() or '<!doctype' in response.lower():
            print("\n✅ Response appears to be valid HTML")
        else:
            print("\n⚠️  Response does not appear to be HTML")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "slp://localhost:4270/"
    success = test_connection(url)
    sys.exit(0 if success else 1)
