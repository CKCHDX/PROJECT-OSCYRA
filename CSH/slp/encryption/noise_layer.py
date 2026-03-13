"""
Noise Protocol Layer.

Third layer of SLP encryption.
Implements Noise_XX pattern for perfect forward secrecy and mutual
authentication using X25519 ECDH.

Changes from v1:
  - Accepts an optional ``static_private_key`` so services can load
    persistent identity keys.
  - Exposes ``handshake_hash`` after key derivation so the outer
    TripleLayerEncryption can derive L1/L2 keys via HKDF.
  - Retains random-nonce encrypt/decrypt for the Noise transport
    channel itself (L3).
"""

import os
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


class NoiseLayer:
    """Noise Protocol XX pattern implementation."""

    def __init__(self, static_private_key: Optional[X25519PrivateKey] = None):
        if static_private_key is not None:
            self.static_private = static_private_key
        else:
            self.static_private = X25519PrivateKey.generate()
        self.static_public = self.static_private.public_key()

        self.remote_static_public: Optional[X25519PublicKey] = None
        self.send_cipher: Optional[ChaCha20Poly1305] = None
        self.recv_cipher: Optional[ChaCha20Poly1305] = None
        self.handshake_complete = False
        self.is_initiator: Optional[bool] = None
        # Raw shared-secret material available after handshake for outer
        # key derivation (L1/L2 keys via HKDF).
        self.handshake_hash: Optional[bytes] = None

    def get_public_key(self) -> bytes:
        return self.static_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    # ── Handshake ─────────────────────────────────────────────────────

    def initiate_handshake(self) -> bytes:
        """Client side: produce the first handshake message (64 bytes)."""
        self.is_initiator = True
        self.ephemeral_private = X25519PrivateKey.generate()
        ephemeral_public = self.ephemeral_private.public_key()
        return (
            ephemeral_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            + self.get_public_key()
        )

    def respond_handshake(self, initiator_message: bytes) -> bytes:
        """Server side: consume INIT, produce RESP (64 bytes)."""
        self.is_initiator = False
        if len(initiator_message) != 64:
            raise ValueError("Invalid handshake INIT message length")

        initiator_ephemeral = X25519PublicKey.from_public_bytes(initiator_message[:32])
        self.remote_static_public = X25519PublicKey.from_public_bytes(initiator_message[32:])

        self.ephemeral_private = X25519PrivateKey.generate()
        ephemeral_public = self.ephemeral_private.public_key()

        shared1 = self.ephemeral_private.exchange(initiator_ephemeral)
        shared2 = self.static_private.exchange(initiator_ephemeral)
        shared3 = self.ephemeral_private.exchange(self.remote_static_public)

        self._derive_keys(shared1 + shared2 + shared3, is_initiator=False)

        response = (
            ephemeral_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            + self.get_public_key()
        )
        self.handshake_complete = True
        return response

    def complete_handshake(self, responder_message: bytes):
        """Client side: consume RESP, complete handshake."""
        if len(responder_message) != 64:
            raise ValueError("Invalid handshake RESP message length")

        responder_ephemeral = X25519PublicKey.from_public_bytes(responder_message[:32])
        self.remote_static_public = X25519PublicKey.from_public_bytes(responder_message[32:])

        shared1 = self.ephemeral_private.exchange(responder_ephemeral)
        shared2 = self.ephemeral_private.exchange(self.remote_static_public)
        shared3 = self.static_private.exchange(responder_ephemeral)

        self._derive_keys(shared1 + shared2 + shared3, is_initiator=True)
        self.handshake_complete = True

    def _derive_keys(self, shared_secret: bytes, is_initiator: bool):
        """Derive L3 send/recv keys and store the handshake hash."""
        # Store raw shared secret hash for outer layers.
        h = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"SLP-Handshake-Hash")
        self.handshake_hash = h.derive(shared_secret)

        # Derive L3 transport keys.
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=None, info=b"SLP-Noise-Keys")
        key_material = hkdf.derive(shared_secret)
        key1, key2 = key_material[:32], key_material[32:]

        if is_initiator:
            self.send_cipher = ChaCha20Poly1305(key1)
            self.recv_cipher = ChaCha20Poly1305(key2)
        else:
            self.send_cipher = ChaCha20Poly1305(key2)
            self.recv_cipher = ChaCha20Poly1305(key1)

    # ── L3 encrypt / decrypt (random nonce) ───────────────────────────

    def encrypt(self, plaintext: bytes) -> bytes:
        if not self.handshake_complete:
            raise RuntimeError("Handshake not complete")
        nonce = os.urandom(12)
        return nonce + self.send_cipher.encrypt(nonce, plaintext, None)

    def decrypt(self, encrypted_data: bytes) -> bytes:
        if not self.handshake_complete:
            raise RuntimeError("Handshake not complete")
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self.recv_cipher.decrypt(nonce, ciphertext, None)
