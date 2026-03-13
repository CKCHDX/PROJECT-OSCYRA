"""Unit tests for slp.encryption.triple_layer."""

import struct
import pytest

from slp.encryption.triple_layer import TripleLayerEncryption


def _handshake_pair():
    """Create a pair of TripleLayerEncryption objects that complete a handshake."""
    initiator = TripleLayerEncryption()
    responder = TripleLayerEncryption()
    msg1 = initiator.initiate_handshake()
    msg2 = responder.respond_handshake(msg1)
    initiator.complete_handshake(msg2)
    return initiator, responder


class TestHandshake:
    def test_handshake_completes(self):
        init, resp = _handshake_pair()
        assert init.handshake_complete is True
        assert resp.handshake_complete is True

    def test_handshake_hash_matches(self):
        init, resp = _handshake_pair()
        assert init.noise.handshake_hash == resp.noise.handshake_hash

    def test_handshake_hash_is_32_bytes(self):
        init, _ = _handshake_pair()
        assert len(init.noise.handshake_hash) == 32


class TestEncryptDecrypt:
    def test_roundtrip(self):
        init, resp = _handshake_pair()
        plaintext = b"Hello, SLP!"
        aad = struct.pack("!IQ", 1, 1)
        ct = init.encrypt(plaintext, counter=1, aad=aad)
        pt = resp.decrypt(ct, counter=1, aad=aad)
        assert pt == plaintext

    def test_roundtrip_responder_to_initiator(self):
        init, resp = _handshake_pair()
        plaintext = b"Response from responder"
        aad = struct.pack("!IQ", 1, 1)
        ct = resp.encrypt(plaintext, counter=1, aad=aad)
        pt = init.decrypt(ct, counter=1, aad=aad)
        assert pt == plaintext

    def test_different_counters_produce_different_ciphertext(self):
        init, _ = _handshake_pair()
        plaintext = b"same data"
        ct1 = init.encrypt(plaintext, counter=1)
        ct2 = init.encrypt(plaintext, counter=2)
        assert ct1 != ct2

    def test_wrong_counter_fails_decrypt(self):
        init, resp = _handshake_pair()
        ct = init.encrypt(b"secret", counter=5, aad=b"\x00" * 12)
        with pytest.raises(Exception):
            resp.decrypt(ct, counter=6, aad=b"\x00" * 12)

    def test_wrong_aad_fails_decrypt(self):
        init, resp = _handshake_pair()
        aad1 = struct.pack("!IQ", 1, 1)
        aad2 = struct.pack("!IQ", 1, 2)
        ct = init.encrypt(b"secret", counter=1, aad=aad1)
        with pytest.raises(Exception):
            resp.decrypt(ct, counter=1, aad=aad2)

    def test_empty_plaintext(self):
        init, resp = _handshake_pair()
        ct = init.encrypt(b"", counter=1)
        assert resp.decrypt(ct, counter=1) == b""

    def test_large_plaintext(self):
        init, resp = _handshake_pair()
        plaintext = b"A" * 10000
        ct = init.encrypt(plaintext, counter=1)
        assert resp.decrypt(ct, counter=1) == plaintext


class TestEncryptBeforeHandshake:
    def test_encrypt_raises(self):
        enc = TripleLayerEncryption()
        with pytest.raises(RuntimeError, match="Handshake not complete"):
            enc.encrypt(b"data")

    def test_decrypt_raises(self):
        enc = TripleLayerEncryption()
        with pytest.raises(RuntimeError, match="Handshake not complete"):
            enc.decrypt(b"data")


class TestRekey:
    def test_rekey_changes_keys(self):
        init, resp = _handshake_pair()
        old_hash = init.noise.handshake_hash

        init.rekey()
        resp.rekey()

        assert init.noise.handshake_hash != old_hash
        assert init.noise.handshake_hash == resp.noise.handshake_hash

    def test_encrypt_decrypt_after_rekey(self):
        init, resp = _handshake_pair()
        init.rekey()
        resp.rekey()
        ct = init.encrypt(b"after-rekey", counter=100)
        assert resp.decrypt(ct, counter=100) == b"after-rekey"

    def test_rekey_before_handshake_raises(self):
        enc = TripleLayerEncryption()
        with pytest.raises(RuntimeError, match="Cannot rekey before handshake"):
            enc.rekey()

    def test_old_keys_fail_after_rekey(self):
        init, resp = _handshake_pair()
        ct = init.encrypt(b"before-rekey", counter=1)
        init.rekey()
        resp.rekey()
        with pytest.raises(Exception):
            resp.decrypt(ct, counter=1)


class TestPublicKey:
    def test_public_key_is_32_bytes(self):
        enc = TripleLayerEncryption()
        assert len(enc.get_public_key()) == 32

    def test_different_instances_different_keys(self):
        a = TripleLayerEncryption()
        b = TripleLayerEncryption()
        assert a.get_public_key() != b.get_public_key()
