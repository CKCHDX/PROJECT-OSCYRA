# SLP - Secure Line Protocol v2

## Overview

SLP (Secure Line Protocol) is a custom triple-layer encrypted UDP protocol for
secure inter-service communication within the CSH (Central Server Hub) ecosystem.
All services communicate exclusively through SLP — no direct HTTP traffic is
permitted between services.

## Packet Format (v2)

### Header — 16 bytes

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Packet Type  |     Flags     |          Session ID           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Session ID (cont.)                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Sequence Number                          |
|                        (64-bit)                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       Payload Length          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Struct format: `"!BBIQH"` (1 + 1 + 4 + 8 + 2 = 16 bytes)

| Field          | Size    | Description                              |
|----------------|---------|------------------------------------------|
| packet_type    | 1 byte  | Message type (see table below)           |
| flags          | 1 byte  | Bitfield flags (ENCRYPTED, COMPRESSED…)  |
| session_id     | 4 bytes | Unique session identifier                |
| sequence       | 8 bytes | Monotonically increasing sequence number |
| payload_length | 2 bytes | Length of the payload following header    |

### Packet Types

| Type | Value  | Direction       | Description                     |
|------|--------|-----------------|---------------------------------|
| HANDSHAKE_INIT | 0x01 | Agent → Gateway | Initiator hello + ephemeral key |
| HANDSHAKE_RESP | 0x02 | Gateway → Agent | Responder hello + ephemeral key |
| HANDSHAKE_FIN  | 0x03 | Agent → Gateway | Final handshake + encrypted REGISTER |
| DATA           | 0x10 | Bidirectional   | Encrypted application data      |
| HEARTBEAT      | 0x20 | Agent → Gateway | Keep-alive with metrics         |
| HEARTBEAT_ACK  | 0x21 | Gateway → Agent | Heartbeat acknowledgement       |
| COMMAND        | 0x30 | Gateway → Agent | Encrypted command from CSH      |
| COMMAND_ACK    | 0x31 | Agent → Gateway | Command acknowledgement         |
| LOG_ENTRY      | 0x40 | Agent → Gateway | Forwarded service log line      |
| REKEY          | 0x50 | Bidirectional   | Session rekeying trigger        |
| CLOSE          | 0xFF | Bidirectional   | Graceful session teardown       |

### Flags

| Flag       | Bit  | Description                           |
|------------|------|---------------------------------------|
| ENCRYPTED  | 0x01 | Payload is triple-layer encrypted     |
| COMPRESSED | 0x02 | Payload is zlib-compressed pre-encrypt|
| FRAGMENTED | 0x04 | Payload is a fragment (not standalone)|
| PRIORITY   | 0x08 | High-priority delivery                |

## Handshake Flow

The handshake follows a three-message exchange based on Noise XX:

```
Agent                                    Gateway
  |                                         |
  |  1. HANDSHAKE_INIT                      |
  |  [ephemeral_pub_key]                    |
  |────────────────────────────────────────>|
  |                                         |  Verify agent pubkey in allow-list
  |  2. HANDSHAKE_RESP                      |
  |  [ephemeral_pub_key + encrypted_static] |
  |<────────────────────────────────────────|
  |                                         |
  |  3. HANDSHAKE_FIN                       |
  |  [encrypted REGISTER payload]           |
  |────────────────────────────────────────>|
  |                                         |  Derive L1/L2 keys from handshake_hash
  |  4. REGISTER_ACK (DATA)                 |
  |  [encrypted ack]                        |
  |<────────────────────────────────────────|
  |                                         |
  |  Session ESTABLISHED                    |
```

### REGISTER Payload (JSON)

```json
{
  "service_id": "klar-001",
  "service_name": "Klar",
  "version": "1.0.0",
  "http_port": 4271,
  "domain": "klar.oscyra.solutions"
}
```

## Session State Machine

```
 ┌──────────┐   HANDSHAKE_INIT    ┌─────────────┐
 │  (new)   │ ──────────────────> │  HANDSHAKE  │
 └──────────┘                     └──────┬──────┘
                                         │ HANDSHAKE_FIN accepted
                                         v
                                  ┌─────────────┐
                           ┌───── │ ESTABLISHED │ <────┐
                           │      └──────┬──────┘      │
                           │             │             │
                    REKEY  │             │ REKEY       │ rekey done
                           v             v             │
                    ┌─────────────┐                    │
                    │  REKEYING   │ ───────────────────┘
                    └─────────────┘
                           │
                    timeout/error
                           v
                    ┌─────────────┐
                    │   CLOSED    │
                    └─────────────┘
```

### Timeouts and Rekey

- **Heartbeat interval**: 10 seconds (agent sends)
- **Session timeout**: 30 seconds without heartbeat → CLOSED
- **Rekey trigger**: 2^32 messages sent OR 1 hour elapsed
- **Reconnect delay**: 3 seconds after CLOSED

## Encryption Layers

### Layer 1 — AES-256-GCM

- Key derived via HKDF-SHA256 from `handshake_hash` with info `"SLP-L1-KEY"`
- 12-byte nonce: 4-byte HKDF-derived prefix (`"SLP-L1-IV"`) + 8-byte big-endian counter
- AAD: `struct.pack("!IQ", session_id, sequence)`

### Layer 2 — ChaCha20-Poly1305

- Key derived via HKDF-SHA256 from `handshake_hash` with info `"SLP-L2-KEY"`
- 12-byte nonce: 4-byte HKDF-derived prefix (`"SLP-L2-IV"`) + 8-byte big-endian counter
- AAD: `struct.pack("!IQ", session_id, sequence)`

### Layer 3 — Noise Protocol (X25519 + AESGCM)

- Transport encryption from the Noise XX handshake
- Random 12-byte nonce per message (generated at encrypt time)
- Provides PFS via ephemeral X25519 keys

### Encryption Order

```
Encrypt: plaintext → L1(AES-GCM) → L2(ChaCha20) → L3(Noise)
Decrypt: ciphertext → L3(Noise) → L2(ChaCha20) → L1(AES-GCM) → plaintext
```

## Key Derivation

After the Noise XX handshake completes, a shared `handshake_hash` is derived:

```python
handshake_hash = HKDF(shared_secret, info=b"SLP-Handshake-Hash", length=32)
```

From this hash, layer keys and IV prefixes are derived:

```
L1 Key     = HKDF(handshake_hash, info=b"SLP-L1-KEY", length=32)
L2 Key     = HKDF(handshake_hash, info=b"SLP-L2-KEY", length=32)
L1 IV Pfx  = HKDF(handshake_hash, info=b"SLP-L1-IV",  length=4)
L2 IV Pfx  = HKDF(handshake_hash, info=b"SLP-L2-IV",  length=4)
```

### Rekeying

Rekeying chains HKDF over the existing hash:

```python
new_hash = HKDF(old_handshake_hash, info=b"SLP-REKEY", length=32)
```

All L1/L2 keys and IV prefixes are re-derived from `new_hash`.

## Replay Protection

- 64-bit monotonic sequence numbers (starting at 1)
- 2048-entry sliding window bitmap
- Sequence 0 is always rejected
- Duplicate sequences within the window are rejected
- Sequences older than `max_seq - 2048` are rejected
- The window advances when a new highest sequence is accepted

## Heartbeat Payload (JSON)

```json
{
  "uptime": 3600.5,
  "requests": 1423,
  "cpu_percent": 12.5,
  "memory_mb": 256.3
}
```

## Command Payload (JSON)

```json
{
  "command": "GRACEFUL_STOP",
  "params": {}
}
```

## Log Entry Payload (JSON)

```json
{
  "level": "INFO",
  "message": "Request processed in 23ms",
  "source": "klar-001",
  "timestamp": "2026-03-13T10:30:00Z"
}
```

## Error Handling and Reconnection

1. **Handshake failure**: Agent waits 3 seconds, then retries with fresh ephemeral keys
2. **Heartbeat timeout**: Gateway marks service as offline after 30 seconds
3. **Decryption failure**: Packet is silently dropped (may indicate tampering)
4. **Unknown public key**: Handshake is rejected at INIT stage
5. **Sequence overflow**: Triggers mandatory rekey
