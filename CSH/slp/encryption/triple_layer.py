"""
Triple-Layer Encryption Orchestrator (v2).

Encryption order:  plaintext → AES-256-GCM (L1) → ChaCha20-Poly1305 (L2) → Noise (L3)
Decryption order:  ciphertext → Noise (L3) → ChaCha20-Poly1305 (L2) → AES-256-GCM (L1)

Key derivation (after Noise handshake):
  - L1 key  = HKDF-SHA256(handshake_hash, info="SLP-L1-KEY",  len=32)
  - L2 key  = HKDF-SHA256(handshake_hash, info="SLP-L2-KEY",  len=32)
  - L1 iv   = HKDF-SHA256(handshake_hash, info="SLP-L1-IV",   len=4)  (nonce prefix)
  - L2 iv   = HKDF-SHA256(handshake_hash, info="SLP-L2-IV",   len=4)  (nonce prefix)

Counter-based nonces (12 bytes each):
  [4-byte HKDF prefix] + [8-byte big-endian counter]
"""

import struct
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from .noise_layer import NoiseLayer


def _hkdf(ikm: bytes, info: bytes, length: int) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=length, salt=None, info=info,
    ).derive(ikm)


class TripleLayerEncryption:
    """Triple-layer encryption with HKDF-derived keys and counter nonces."""

    def __init__(self, static_private_key: Optional[X25519PrivateKey] = None):
        self.noise = NoiseLayer(static_private_key=static_private_key)
        self.handshake_complete = False

        # Derived after handshake.
        self._l1: Optional[AESGCM] = None
        self._l2: Optional[ChaCha20Poly1305] = None
        self._l1_iv_prefix: bytes = b""
        self._l2_iv_prefix: bytes = b""

    # ── Public key access ─────────────────────────────────────────────

    def get_public_key(self) -> bytes:
        return self.noise.get_public_key()

    # ── Handshake passthrough ─────────────────────────────────────────

    def initiate_handshake(self) -> bytes:
        return self.noise.initiate_handshake()

    def respond_handshake(self, initiator_message: bytes) -> bytes:
        response = self.noise.respond_handshake(initiator_message)
        self._derive_layers()
        return response

    def complete_handshake(self, responder_message: bytes):
        self.noise.complete_handshake(responder_message)
        self._derive_layers()

    def _derive_layers(self):
        hh = self.noise.handshake_hash
        if hh is None:
            raise RuntimeError("No handshake hash available")
        self._l1 = AESGCM(_hkdf(hh, b"SLP-L1-KEY", 32))
        self._l2 = ChaCha20Poly1305(_hkdf(hh, b"SLP-L2-KEY", 32))
        self._l1_iv_prefix = _hkdf(hh, b"SLP-L1-IV", 4)
        self._l2_iv_prefix = _hkdf(hh, b"SLP-L2-IV", 4)
        self.handshake_complete = True

    # ── Rekey ─────────────────────────────────────────────────────────

    def rekey(self):
        """Derive fresh L1/L2 keys from a new HKDF round over the
        existing handshake hash.  Does NOT re-handshake Noise."""
        if not self.handshake_complete:
            raise RuntimeError("Cannot rekey before handshake")
        hh = self.noise.handshake_hash
        # Chain: new_hh = HKDF(old_hh, info="SLP-REKEY")
        new_hh = _hkdf(hh, b"SLP-REKEY", 32)
        self.noise.handshake_hash = new_hh
        self._l1 = AESGCM(_hkdf(new_hh, b"SLP-L1-KEY", 32))
        self._l2 = ChaCha20Poly1305(_hkdf(new_hh, b"SLP-L2-KEY", 32))
        self._l1_iv_prefix = _hkdf(new_hh, b"SLP-L1-IV", 4)
        self._l2_iv_prefix = _hkdf(new_hh, b"SLP-L2-IV", 4)

    # ── Nonce construction ────────────────────────────────────────────

    @staticmethod
    def _make_nonce(prefix: bytes, counter: int) -> bytes:
        """4-byte prefix + 8-byte big-endian counter = 12-byte nonce."""
        return prefix + struct.pack("!Q", counter)

    # ── Encrypt / Decrypt ─────────────────────────────────────────────

    def encrypt(self, plaintext: bytes, counter: int = 0, aad: Optional[bytes] = None) -> bytes:
        """Encrypt through L1 → L2 → L3."""
        if not self.handshake_complete:
            raise RuntimeError("Handshake not complete")
        nonce1 = self._make_nonce(self._l1_iv_prefix, counter)
        nonce2 = self._make_nonce(self._l2_iv_prefix, counter)

        l1_out = self._l1.encrypt(nonce1, plaintext, aad)
        l2_out = self._l2.encrypt(nonce2, l1_out, aad)
        l3_out = self.noise.encrypt(l2_out)
        return l3_out

    def decrypt(self, ciphertext: bytes, counter: int = 0, aad: Optional[bytes] = None) -> bytes:
        """Decrypt through L3 → L2 → L1."""
        if not self.handshake_complete:
            raise RuntimeError("Handshake not complete")
        nonce1 = self._make_nonce(self._l1_iv_prefix, counter)
        nonce2 = self._make_nonce(self._l2_iv_prefix, counter)

        l2_out = self.noise.decrypt(ciphertext)
        l1_out = self._l2.decrypt(nonce2, l2_out, aad)
        plaintext = self._l1.decrypt(nonce1, l1_out, aad)
        return plaintext
