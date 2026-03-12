#!/usr/bin/env python3
"""
AES-256-GCM Encryption Layer

First layer of SLP encryption.
Uses AES-256 in GCM mode for authenticated encryption.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Tuple


class AESLayer:
    """AES-256-GCM encryption layer."""
    
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits (recommended for GCM)
    TAG_SIZE = 16  # 128 bits authentication tag
    
    def __init__(self, key: bytes = None):
        """
        Initialize AES encryption layer.
        
        Args:
            key: 32-byte encryption key (auto-generated if None)
        """
        if key is None:
            key = os.urandom(self.KEY_SIZE)
        elif len(key) != self.KEY_SIZE:
            raise ValueError(f"Key must be {self.KEY_SIZE} bytes")
        
        self.key = key
        self.cipher = AESGCM(key)
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a random 256-bit key."""
        return os.urandom(AESLayer.KEY_SIZE)
    
    @staticmethod
    def derive_key(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """
        Derive key from password using PBKDF2.
        
        Args:
            password: Password string
            salt: Salt bytes (auto-generated if None)
            
        Returns:
            tuple: (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=AESLayer.KEY_SIZE,
            salt=salt,
            iterations=100000  # OWASP recommendation
        )
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def encrypt(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        """
        Encrypt data with AES-256-GCM.
        
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
        Decrypt AES-256-GCM encrypted data.
        
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
            raise Exception(f"Decryption failed (data may be corrupted or tampered): {e}")


if __name__ == "__main__":
    # Test AES encryption
    print("Testing AES-256-GCM Encryption...\n")
    
    # Generate key
    key = AESLayer.generate_key()
    print(f"Generated key: {key.hex()[:32]}...")
    
    # Create cipher
    aes = AESLayer(key)
    
    # Test encryption
    plaintext = b"This is a secret message for SLP protocol testing!"
    print(f"\nPlaintext: {plaintext.decode()}")
    
    encrypted = aes.encrypt(plaintext)
    print(f"Encrypted: {encrypted.hex()[:64]}... ({len(encrypted)} bytes)")
    
    # Test decryption
    decrypted = aes.decrypt(encrypted)
    print(f"Decrypted: {decrypted.decode()}")
    
    # Verify
    assert plaintext == decrypted
    print("\n✅ AES-256-GCM test passed!")
    
    # Test with associated data
    print("\nTesting with associated data...")
    associated = b"SLP-v1.0"
    encrypted_ad = aes.encrypt(plaintext, associated)
    decrypted_ad = aes.decrypt(encrypted_ad, associated)
    assert plaintext == decrypted_ad
    print("✅ Associated data authentication passed!")
