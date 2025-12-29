"""Encryption utilities for sensitive data."""

import os
import base64
from typing import Union
from cryptography.fernet import Fernet
from app.config import get_settings

settings = get_settings()


def _get_cipher() -> Fernet:
    """Get Fernet cipher instance."""
    encryption_key = os.environ.get('ENCRYPTION_KEY') or settings.encryption_key

    if not encryption_key:
        raise ValueError(
            "ENCRYPTION_KEY is not configured. Please set the ENCRYPTION_KEY environment variable. "
            "Generate a secure key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    if isinstance(encryption_key, str):
        encryption_key = encryption_key.encode()

    # Validate key is proper Fernet format (32 bytes base64 encoded = 44 characters)
    # Security: Do NOT pad short keys as this reduces entropy and creates vulnerabilities
    if len(encryption_key) != 44:
        raise ValueError(
            f"ENCRYPTION_KEY must be exactly 44 characters (got {len(encryption_key)}). "
            "Padding short keys is a security risk. "
            "Generate a proper key with: python scripts/generate_security_keys.py --only-encryption"
        )

    try:
        return Fernet(encryption_key)
    except Exception as e:
        raise ValueError(
            f"Invalid ENCRYPTION_KEY format: {e}. "
            "Generate a valid Fernet key with: python scripts/generate_security_keys.py --only-encryption"
        )


def encrypt_string(plaintext: str) -> str:
    """Encrypt string and return base64-encoded result."""
    cipher = _get_cipher()
    encrypted = cipher.encrypt(plaintext.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_string(encrypted_text: str) -> str:
    """Decrypt base64-encoded encrypted string."""
    cipher = _get_cipher()
    try:
        encrypted = base64.b64decode(encrypted_text.encode())
        decrypted = cipher.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt string: {e}")
