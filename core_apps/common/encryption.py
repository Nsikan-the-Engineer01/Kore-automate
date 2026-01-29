"""
Encryption utilities for PayWithAccount API.

Provides TripleDES encryption for the 'secure' field in auth objects.
"""
import base64
import hashlib
from typing import Optional

from django.conf import settings


def encrypt_secure_field(account_number: str, cbn_bankcode: str, secret_key: Optional[str] = None) -> str:
    """
    Encrypt account details using TripleDES for PayWithAccount API.

    The plaintext format is: "{account_number};{cbn_bankcode}"
    Encryption uses TripleDES/CBC/PKCS5Padding with MD5-derived key.

    Args:
        account_number: Customer bank account number.
        cbn_bankcode: CBN bank code.
        secret_key: Encryption secret key. If not provided, reads from
                   settings.PWA_CLIENT_SECRET.

    Returns:
        Base64-encoded encrypted string.
    """
    try:
        from Crypto.Cipher import DES3
        from Crypto.Util.Padding import pad
    except ImportError:
        raise ImportError(
            "pycryptodome is required for PayWithAccount encryption. "
            "Install it with: pip install pycryptodome"
        )

    if secret_key is None:
        secret_key = getattr(settings, "PWA_CLIENT_SECRET", "")

    if not secret_key:
        raise ValueError("Secret key is required for encryption")

    # Prepare plaintext
    plaintext = f"{account_number};{cbn_bankcode}"

    # Derive key using MD5 (UTF-16LE encoding)
    key_source = secret_key.encode("utf-16le")
    md5_hash = hashlib.md5(key_source).digest()
    # Extend to 24 bytes for TripleDES
    key = md5_hash + md5_hash[:8]

    # IV is 8 zero bytes
    iv = b"\x00" * 8

    # Encrypt
    cipher = DES3.new(key, DES3.MODE_CBC, iv)
    padded_plaintext = pad(plaintext.encode("utf-16le"), DES3.block_size)
    ciphertext = cipher.encrypt(padded_plaintext)

    # Return base64-encoded result
    return base64.b64encode(ciphertext).decode("utf-8")
