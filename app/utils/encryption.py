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

    # Ensure key is proper length (32 bytes base64 encoded = 44 characters)
    if len(encryption_key) < 44:
        # Pad the key if it's too short, but log a warning
        import logging
        logging.warning("ENCRYPTION_KEY is shorter than recommended. Using padded key.")
        encryption_key = base64.urlsafe_b64encode(encryption_key.ljust(32)[:32])

    return Fernet(encryption_key)


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
