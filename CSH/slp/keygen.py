"""
SLP Key Generation Utility.

Generates X25519 keypairs for CSH and services.

CLI usage:
    python -m slp.keygen --name klar --output-dir keys/
"""

import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


def generate_keypair() -> tuple:
    """Return (private_key, public_key) as X25519 objects."""
    private = X25519PrivateKey.generate()
    public = private.public_key()
    return private, public


def save_keypair(name: str, output_dir: str):
    """Generate and save a keypair to *output_dir*/{name}_private.key and {name}_public.key."""
    os.makedirs(output_dir, exist_ok=True)
    private, public = generate_keypair()

    priv_path = os.path.join(output_dir, f"{name}_private.key")
    pub_path = os.path.join(output_dir, f"{name}_public.key")

    priv_bytes = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    with open(priv_path, "wb") as f:
        f.write(priv_bytes)
    with open(pub_path, "wb") as f:
        f.write(pub_bytes)

    # Restrict private key permissions on Unix.
    try:
        os.chmod(priv_path, 0o600)
    except OSError:
        pass

    return priv_path, pub_path


def load_private_key(path: str) -> X25519PrivateKey:
    """Load an X25519 private key from a raw 32-byte file."""
    with open(path, "rb") as f:
        raw = f.read()
    return X25519PrivateKey.from_private_bytes(raw)


def load_public_key(path: str) -> X25519PublicKey:
    """Load an X25519 public key from a raw 32-byte file."""
    with open(path, "rb") as f:
        raw = f.read()
    return X25519PublicKey.from_public_bytes(raw)


def load_public_key_bytes(path: str) -> bytes:
    """Load raw public key bytes from file."""
    with open(path, "rb") as f:
        return f.read()


def ensure_keys(output_dir: str, names: list):
    """Generate keypairs for any *names* that don't already have keys."""
    generated = []
    for name in names:
        priv_path = os.path.join(output_dir, f"{name}_private.key")
        pub_path = os.path.join(output_dir, f"{name}_public.key")
        if not os.path.exists(priv_path) or not os.path.exists(pub_path):
            save_keypair(name, output_dir)
            generated.append(name)
    return generated


def main():
    parser = argparse.ArgumentParser(description="SLP Key Generation")
    parser.add_argument("--name", required=True, help="Key name (e.g. 'csh', 'klar')")
    parser.add_argument("--output-dir", default="keys", help="Output directory")
    args = parser.parse_args()

    priv_path, pub_path = save_keypair(args.name, args.output_dir)
    print(f"Generated keypair for '{args.name}':")
    print(f"  Private: {priv_path}")
    print(f"  Public:  {pub_path}")


if __name__ == "__main__":
    main()
