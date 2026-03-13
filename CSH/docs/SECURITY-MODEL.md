# Security Model — CSH / SLP

## Zero-Trust Principles

1. **No implicit trust**: Every service must authenticate via mutual X25519 key exchange
2. **Loopback only**: All services bind exclusively to `127.0.0.1` — no direct external access
3. **Encrypted by default**: All inter-service traffic uses triple-layer encryption
4. **Pinned keys**: The gateway maintains an allow-list of known service public keys
5. **No HTTP bypass**: Services are only reachable through the CSH reverse proxy

## Threat Model

| Threat                        | Mitigation                                       | Layer     |
|-------------------------------|--------------------------------------------------|-----------|
| Eavesdropping on local traffic| Triple-layer encryption (AES-GCM + ChaCha20 + Noise) | L1-L3 |
| Replay attacks                | 64-bit sequence numbers + 2048-bit sliding window| Protocol  |
| Man-in-the-middle             | Mutual authentication via pinned X25519 keys     | Handshake |
| Service impersonation         | Public key allow-list at gateway                 | Gateway   |
| Direct service access         | 127.0.0.1 binding + firewall rules               | Network   |
| CORS abuse                    | Restrictive origin lists per service             | HTTP      |
| Key compromise (forward secrecy) | Ephemeral X25519 keys per session (PFS)       | Noise XX  |
| Long-lived key exposure       | Automatic rekeying (2^32 msgs or 1 hour)         | Protocol  |
| Nonce reuse                   | Counter-based nonces with HKDF-derived prefixes  | Encryption|
| UDP amplification             | Authenticated sessions only; no response to unknown peers | Gateway |
| Denial of service             | Rate limiting, heartbeat timeout (30s)           | Gateway   |

## Cryptographic Construction

### Why Triple-Layer?

Each layer addresses a distinct concern:

- **Layer 1 (AES-256-GCM)**: Hardware-accelerated authenticated encryption. Provides the
  primary confidentiality and integrity guarantee with AES-NI on modern CPUs.
- **Layer 2 (ChaCha20-Poly1305)**: Software-optimized AEAD. Acts as a defense-in-depth
  layer — if AES is compromised (side-channel, implementation flaw), ChaCha20 provides
  an independent cipher.
- **Layer 3 (Noise XX)**: Handles key agreement and transport encryption. Provides
  perfect forward secrecy through ephemeral X25519 Diffie-Hellman.

### Nonce Construction

L1 and L2 use deterministic counter-based nonces to prevent nonce reuse:

```
nonce (12 bytes) = HKDF_prefix (4 bytes) || counter (8 bytes, big-endian)
```

- The prefix is unique per session (derived from `handshake_hash`)
- The counter is monotonically increasing per direction
- L3 uses random 12-byte nonces (safe because L3 keys are ephemeral)

### Associated Authenticated Data (AAD)

```python
aad = struct.pack("!IQ", session_id, sequence_number)
```

This binds ciphertext to the specific session and sequence, preventing
cross-session or cross-sequence splicing.

## Key Management

### Key Generation

- X25519 keypairs are generated using `cryptography.hazmat.primitives.asymmetric.x25519`
- Private keys are stored as 32-byte raw files with restrictive permissions (chmod 600)
- Public keys are stored as 32-byte raw files (readable)

### Key Storage Layout

```
CSH/keys/
  csh.key          # CSH gateway private key (chmod 600)
  csh.pub          # CSH gateway public key
  klar.key         # Klar service private key
  klar.pub         # Klar service public key
  sverkan.key      # Sverkan service private key
  sverkan.pub      # Sverkan service public key
  upsum.key        # Upsum service private key
  upsum.pub        # Upsum service public key
```

### Key Lifecycle

1. **First run**: CSH generates all keypairs if they don't exist
2. **Service registration**: Agent presents its static public key during handshake
3. **Session keys**: Derived via HKDF from the Noise handshake shared secret
4. **Rekeying**: Triggered after 2^32 messages or 1 hour; chains HKDF over existing material
5. **Rotation**: Manual process — regenerate keys and redistribute

## Network Architecture

```
Internet
    │
    │  HTTPS (port 443, via Caddy)
    v
┌──────────────────────────┐
│  CSH Reverse Proxy       │  127.0.0.1:5000
│  Host-header routing     │
│  ┌────────────────────┐  │
│  │ SLP Gateway        │  │  UDP 127.0.0.1:14270
│  │ (triple-layer enc) │  │
│  └────────┬───────────┘  │
└───────────┼──────────────┘
            │ SLP (encrypted UDP)
     ┌──────┼──────┬──────────┐
     v      v      v          v
  ┌─────┐┌─────┐┌─────┐ ┌────────┐
  │Klar ││Svkn ││Upsum│ │Testview│
  │:4271││:4272││:4273│ │:4274   │
  └─────┘└─────┘└─────┘ └────────┘
  All on 127.0.0.1 only
```

## Security Checklist

- [ ] No service binds `0.0.0.0`
- [ ] No plain-HTTP paths bypass CSH reverse proxy
- [ ] CORS origins are restrictive (not `*`)
- [ ] Sequence numbers are monotonic and replays are rejected
- [ ] Unknown public keys are rejected at handshake
- [ ] Private keys are not readable by other users
- [ ] Rekeying triggers before nonce space exhaustion
- [ ] Dashboard does not expose sensitive cryptographic material
