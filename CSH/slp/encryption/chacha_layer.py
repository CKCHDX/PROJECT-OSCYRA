#!/usr/bin/env python3
"""
ChaCha20-Poly1305 Encryption Layer

Second layer of SLP encryption.
Uses ChaCha20-Poly1305 for high-performance authenticated encryption.
Faster than AES on systems without hardware AES support.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from typing import Tuple


class ChaChaLayer:
    """ChaCha20-Poly1305 encryption layer."""
    
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits
    TAG_SIZE = 16  # 128 bits authentication tag
    
    def __init__(self, key: bytes = None):
        """
        Initialize ChaCha20-Poly1305 encryption layer.
        
        Args:
            key: 32-byte encryption key (auto-generated if None)
        """
        if key is None:
            key = os.urandom(self.KEY_SIZE)
        elif len(key) != self.KEY_SIZE:
            raise ValueError(f"Key must be {self.KEY_SIZE} bytes")
        
        self.key = key
        self.cipher = ChaCha20Poly1305(key)
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a random 256-bit key."""
        return os.urandom(ChaChaLayer.KEY_SIZE)
    
    def encrypt(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        """
        Encrypt data with ChaCha20-Poly1305.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Optional authenticated data (not encrypted)
            
        Returns:
            bytes: nonce (12 bytes) + ciphertext + tag (16 bytes)
        """
        # Generate random nonce
        nonce = os.urandom(self.NONCE_SIZE)
        
        # Encrypt and authenticate
        ciphertext = self.cipher.encrypt(nonce, plaintext, associated_data)
        
        # Return: nonce + ciphertext (includes authentication tag)
        return nonce + ciphertext
    
    def decrypt(self, encrypted_data: bytes, associated_data: bytes = None) -> bytes:
        """
        Decrypt ChaCha20-Poly1305 encrypted data.
        
        Args:
            encrypted_data: nonce + ciphertext + tag
            associated_data: Optional authenticated data
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            Exception: If authentication fails or data is corrupted
        """
        if len(encrypted_data) < self.NONCE_SIZE + self.TAG_SIZE:
            raise ValueError("Encrypted data too short")
        
        # Extract nonce and ciphertext
        nonce = encrypted_data[:self.NONCE_SIZE]
        ciphertext = encrypted_data[self.NONCE_SIZE:]
        
        # Decrypt and verify authentication tag
        try:
            plaintext = self.cipher.decrypt(nonce, ciphertext, associated_data)
            return plaintext
        except Exception as e:
            raise Exception(f"Decryption failed: {e}")


if __name__ == "__main__":
    # Test ChaCha20-Poly1305 encryption
    print("Testing ChaCha20-Poly1305 Encryption...\n")
    
    # Generate key
    key = ChaChaLayer.generate_key()
    print(f"Generated key: {key.hex()[:32]}...")
    
    # Create cipher
    chacha = ChaChaLayer(key)
    
    # Test encryption
    plaintext = b"ChaCha20 is faster than AES on most devices!"
    print(f"\nPlaintext: {plaintext.decode()}")
    
    encrypted = chacha.encrypt(plaintext)
    print(f"Encrypted: {encrypted.hex()[:64]}... ({len(encrypted)} bytes)")
    
    # Test decryption
    decrypted = chacha.decrypt(encrypted)
    print(f"Decrypted: {decrypted.decode()}")
    
    # Verify
    assert plaintext == decrypted
    print("\n✅ ChaCha20-Poly1305 test passed!")
