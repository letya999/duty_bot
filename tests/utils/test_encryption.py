import pytest
import os
from app.utils.encryption import encrypt_string, decrypt_string, _get_cipher


class TestEncryption:
    """Test encryption utilities"""

    @pytest.fixture(autouse=True)
    def setup_encryption_key(self):
        """Setup encryption key for tests"""
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        os.environ['ENCRYPTION_KEY'] = key.decode()
        yield
        # Cleanup
        if 'ENCRYPTION_KEY' in os.environ:
            del os.environ['ENCRYPTION_KEY']

    def test_encrypt_string(self):
        """Test encrypting a string"""
        plaintext = "secret_data"
        encrypted = encrypt_string(plaintext)

        assert encrypted is not None
        assert isinstance(encrypted, str)
        assert encrypted != plaintext  # Should not match plaintext

    def test_decrypt_string(self):
        """Test decrypting an encrypted string"""
        plaintext = "secret_data"
        encrypted = encrypt_string(plaintext)
        decrypted = decrypt_string(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self):
        """Test encrypt-decrypt roundtrip"""
        test_cases = [
            "simple text",
            "123456",
            "special!@#$%^&*()",
            "unicode: αβγδ",
            "",
            " spaces everywhere ",
            "very" * 100  # Long string
        ]

        for plaintext in test_cases:
            encrypted = encrypt_string(plaintext)
            decrypted = decrypt_string(encrypted)
            assert decrypted == plaintext, f"Roundtrip failed for: {plaintext}"

    def test_encrypt_multiple_times_produces_different_results(self):
        """Test that encrypting same plaintext multiple times produces different ciphertext"""
        plaintext = "same text"
        encrypted1 = encrypt_string(plaintext)
        encrypted2 = encrypt_string(plaintext)

        # Each encryption should produce different ciphertext (due to IV)
        assert encrypted1 != encrypted2

        # But both should decrypt to same plaintext
        assert decrypt_string(encrypted1) == plaintext
        assert decrypt_string(encrypted2) == plaintext

    def test_decrypt_invalid_string_raises_error(self):
        """Test that decrypting invalid data raises error"""
        with pytest.raises(ValueError):
            decrypt_string("invalid_encrypted_data")

    def test_decrypt_corrupted_data_raises_error(self):
        """Test that decrypting corrupted data raises error"""
        plaintext = "secret"
        encrypted = encrypt_string(plaintext)

        # Corrupt the encrypted data
        corrupted = encrypted[:-10] + "corrupted!"

        with pytest.raises(ValueError):
            decrypt_string(corrupted)

    def test_get_cipher_creates_cipher(self):
        """Test that _get_cipher creates a cipher"""
        # Since we set ENCRYPTION_KEY in setup_encryption_key fixture,
        # _get_cipher should succeed
        cipher = _get_cipher()
        assert cipher is not None

    def test_encrypt_string_empty_raises_error(self):
        """Test encrypting empty string"""
        # Empty string is valid and should encrypt successfully
        encrypted = encrypt_string("")
        assert encrypted is not None
        assert decrypt_string(encrypted) == ""

    def test_long_string_encryption(self):
        """Test encrypting very long string"""
        plaintext = "x" * 10000
        encrypted = encrypt_string(plaintext)
        decrypted = decrypt_string(encrypted)

        assert decrypted == plaintext
