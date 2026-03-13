# SLP Examples - Proof of Concept

Simple examples to test SLP (Secure Line Protocol) communication.

## Files

- `server.py` - Basic UDP server for testing
- `client.py` - Simple client to test connectivity
- `test_connection.py` - Automated connection test

## Quick Start

### 1. Start the Server

Open a terminal and run:

```bash
python examples/server.py
```

You should see:
```
[14:30:45] ✅ SLP Server started
[14:30:45] 🔊 Listening on 0.0.0.0:4270
[14:30:45] 📦 Buffer size: 4096 bytes
[14:30:45]
[14:30:45] Waiting for connections...
[14:30:45] Press Ctrl+C to stop
[14:30:45] ==================================================
```

### 2. Test Connection

Open another terminal and run:

```bash
python examples/test_connection.py
```

Expected output:
```
Testing SLP connection...
Target: localhost:4270

[1/3] Sending test message...
[2/3] Waiting for response...
[3/3] Verifying response...

✅ SUCCESS!
   Received 456 bytes
   Server: 127.0.0.1:4270

🎉 SLP server is working!
```

### 3. Full Client Test

```bash
python examples/client.py
```

Or connect to a specific server:

```bash
python examples/client.py 192.168.1.100 4270
```

## What This Tests

- ✅ UDP socket communication
- ✅ Basic request/response flow
- ✅ Packet sending and receiving
- ✅ Network connectivity

## Next Steps

Once this works:

1. Add packet structure (see `slp/protocol/packet.py`)
2. Add basic encryption (AES-256-GCM)
3. Integrate with Qt WebEngine client
4. Test custom address format (`slp://klar.local`)

## Troubleshooting

### Connection Timeout

- Make sure server is running
- Check firewall allows UDP port 4270
- Try `localhost` instead of IP address

### Port Already in Use

- Stop existing server: Ctrl+C
- Or change port in both server.py and client.py

### Permission Denied

- On Linux/Mac: Don't use port < 1024 without sudo
- Port 4270 should work without special permissions

## Current Status

**Phase 0: Proof of Concept**
- ✅ Basic UDP server
- ✅ Basic UDP client
- ✅ Simple request/response
- ⚠️ No encryption yet
- ⚠️ No packet structure yet
- ⚠️ No Qt integration yet

This is the foundation. Once this works reliably, we'll add:
- Packet format
- Encryption
- Qt WebEngine integration
- Full CSH integration
