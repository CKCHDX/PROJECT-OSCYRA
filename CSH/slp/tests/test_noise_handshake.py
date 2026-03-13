"""Unit tests for slp.encryption.noise_layer."""

import pytest

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from slp.encryption.noise_layer import NoiseLayer


def _handshake_pair(init_key=None, resp_key=None):
    """Perform a full Noise XX handshake between two peers."""
    init = NoiseLayer(static_private_key=init_key)
    resp = NoiseLayer(static_private_key=resp_key)
    msg1 = init.initiate_handshake()
    msg2 = resp.respond_handshake(msg1)
    init.complete_handshake(msg2)
    return init, resp


class TestHandshake:
    def test_completes_successfully(self):
        init, resp = _handshake_pair()
        assert init.handshake_complete is True
        assert resp.handshake_complete is True

    def test_handshake_init_message_is_64_bytes(self):
        layer = NoiseLayer()
        msg = layer.initiate_handshake()
        assert len(msg) == 64

    def test_handshake_resp_message_is_64_bytes(self):
        init = NoiseLayer()
        resp = NoiseLayer()
        msg1 = init.initiate_handshake()
        msg2 = resp.respond_handshake(msg1)
        assert len(msg2) == 64

    def test_invalid_init_message_length(self):
        resp = NoiseLayer()
        with pytest.raises(ValueError, match="Invalid handshake INIT"):
            resp.respond_handshake(b"\x00" * 32)

    def test_invalid_resp_message_length(self):
        init = NoiseLayer()
        init.initiate_handshake()
        with pytest.raises(ValueError, match="Invalid handshake RESP"):
            init.complete_handshake(b"\x00" * 48)

    def test_handshake_hash_derived(self):
        init, resp = _handshake_pair()
        assert init.handshake_hash is not None
        assert resp.handshake_hash is not None
        assert len(init.handshake_hash) == 32
        assert init.handshake_hash == resp.handshake_hash

    def test_remote_static_public_populated(self):
        init, resp = _handshake_pair()
        assert init.remote_static_public is not None
        assert resp.remote_static_public is not None

    def test_persistent_keys(self):
        key1 = X25519PrivateKey.generate()
        key2 = X25519PrivateKey.generate()
        init, resp = _handshake_pair(init_key=key1, resp_key=key2)
        assert init.handshake_complete


class TestL3EncryptDecrypt:
    def test_roundtrip(self):
        init, resp = _handshake_pair()
        ct = init.encrypt(b"hello noise")
        pt = resp.decrypt(ct)
        assert pt == b"hello noise"

    def test_roundtrip_resp_to_init(self):
        init, resp = _handshake_pair()
        ct = resp.encrypt(b"response")
        pt = init.decrypt(ct)
        assert pt == b"response"

    def test_encrypt_before_handshake_raises(self):
        layer = NoiseLayer()
        with pytest.raises(RuntimeError, match="Handshake not complete"):
            layer.encrypt(b"data")

    def test_decrypt_before_handshake_raises(self):
        layer = NoiseLayer()
        with pytest.raises(RuntimeError, match="Handshake not complete"):
            layer.decrypt(b"\x00" * 28)

    def test_tampered_ciphertext_fails(self):
        init, resp = _handshake_pair()
        ct = init.encrypt(b"important data")
        # Flip a byte in the ciphertext (after the 12-byte nonce).
        tampered = ct[:15] + bytes([ct[15] ^ 0xFF]) + ct[16:]
        with pytest.raises(Exception):
            resp.decrypt(tampered)

    def test_empty_plaintext(self):
        init, resp = _handshake_pair()
        ct = init.encrypt(b"")
        assert resp.decrypt(ct) == b""

    def test_ciphertext_contains_12_byte_nonce(self):
        init, _ = _handshake_pair()
        ct = init.encrypt(b"test")
        # ChaCha20-Poly1305: 12 nonce + len(plaintext) + 16 tag
        assert len(ct) == 12 + 4 + 16


class TestPublicKey:
    def test_public_key_32_bytes(self):
        layer = NoiseLayer()
        assert len(layer.get_public_key()) == 32

    def test_persistent_key_matches(self):
        key = X25519PrivateKey.generate()
        layer = NoiseLayer(static_private_key=key)
        from cryptography.hazmat.primitives import serialization
        expected = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        assert layer.get_public_key() == expected


class TestIsInitiator:
    def test_initiator_flag(self):
        init, resp = _handshake_pair()
        assert init.is_initiator is True
        assert resp.is_initiator is False
