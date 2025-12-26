#!/usr/bin/env python3
"""
Security Keys Generator for Duty Bot

This script generates all required cryptographic keys and tokens for secure
operation of the Duty Bot application.

Usage:
    python scripts/generate_security_keys.py
    python scripts/generate_security_keys.py --output .env.security
"""

import argparse
import base64
import secrets
import sys
from pathlib import Path


class SecurityKeysGenerator:
    """Generate cryptographic keys and security tokens"""

    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generate a secure encryption key for Fernet encryption.

        This key is used to encrypt sensitive data like Google Calendar
        service account credentials stored in the database.

        Returns:
            Base64-encoded 32-byte encryption key
        """
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key().decode()
        except BaseException as e:
            # Fallback if cryptography is not available or has any issues
            # Using BaseException to catch even SystemExit, KeyboardInterrupt, etc from cryptography
            if not isinstance(e, (ImportError, ModuleNotFoundError)):
                print("\n⚠️  Warning: cryptography library error (possibly broken installation)", file=sys.stderr)
            else:
                print("\n⚠️  Warning: cryptography library not installed", file=sys.stderr)
            print(f"   Error: {type(e).__name__}: {e}", file=sys.stderr)
            print("\n   Using fallback method (secrets module)", file=sys.stderr)
            print("   This is secure but you may want to reinstall cryptography:", file=sys.stderr)
            print("   pip install --force-reinstall cryptography\n", file=sys.stderr)
            # Generate a 32-byte key and base64 encode it (Fernet format)
            key = secrets.token_bytes(32)
            return base64.urlsafe_b64encode(key).decode()

    @staticmethod
    def generate_secret_key(length: int = 64) -> str:
        """
        Generate a cryptographically secure random secret key.

        Args:
            length: Number of bytes for the secret (default: 64)

        Returns:
            URL-safe base64-encoded random string
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_api_token(length: int = 32) -> str:
        """
        Generate a secure API token.

        Args:
            length: Number of bytes for the token (default: 32)

        Returns:
            URL-safe base64-encoded random string
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_session_secret(length: int = 32) -> str:
        """
        Generate a session secret for cookie signing.

        Args:
            length: Number of bytes for the secret (default: 32)

        Returns:
            URL-safe base64-encoded random string
        """
        return secrets.token_urlsafe(length)

    def generate_all_keys(self) -> dict:
        """
        Generate all required security keys.

        Returns:
            Dictionary with all generated keys
        """
        return {
            'ENCRYPTION_KEY': self.generate_encryption_key(),
            'SECRET_KEY': self.generate_secret_key(),
            'SESSION_SECRET': self.generate_session_secret(),
            'API_TOKEN': self.generate_api_token(),
        }

    def display_keys(self, keys: dict, show_explanation: bool = True):
        """
        Display generated keys with explanations.

        Args:
            keys: Dictionary of generated keys
            show_explanation: Whether to show usage explanations
        """
        print("\n" + "=" * 80)
        print("🔐 SECURITY KEYS GENERATED")
        print("=" * 80)
        print("\nADD THESE TO YOUR .env FILE:\n")
        print("-" * 80)

        explanations = {
            'ENCRYPTION_KEY': (
                'Used to encrypt sensitive data (Google Calendar credentials)\n'
                '        CRITICAL: Keep this secret and secure. Loss means data cannot be decrypted.'
            ),
            'SECRET_KEY': (
                'General-purpose secret for application security\n'
                '        Used for session signing and other cryptographic operations.'
            ),
            'SESSION_SECRET': (
                'Secret for signing session cookies\n'
                '        Ensures session cookies cannot be tampered with.'
            ),
            'API_TOKEN': (
                'Token for API authentication (if using external API access)\n'
                '        Optional: Only needed if you enable token-based API access.'
            ),
        }

        for key, value in keys.items():
            if show_explanation and key in explanations:
                print(f"\n# {explanations[key]}")
            print(f"{key}={value}")
            print()

        print("-" * 80)
        print("\n⚠️  SECURITY WARNINGS:")
        print("   1. NEVER commit these keys to version control")
        print("   2. NEVER share these keys publicly")
        print("   3. Store them securely (password manager, secrets vault)")
        print("   4. Use different keys for development and production")
        print("   5. Rotate keys periodically (every 6-12 months)")
        print("\n" + "=" * 80)

    def save_to_file(self, keys: dict, filepath: str):
        """
        Save generated keys to a file.

        Args:
            keys: Dictionary of generated keys
            filepath: Path to save the keys
        """
        path = Path(filepath)

        # Check if file exists
        if path.exists():
            response = input(f"\n⚠️  File {filepath} already exists. Overwrite? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Aborted. Keys not saved.")
                return

        # Create backup if file exists
        if path.exists():
            backup_path = path.with_suffix('.bak')
            path.rename(backup_path)
            print(f"✅ Backup created: {backup_path}")

        # Write keys to file
        with open(filepath, 'w') as f:
            f.write("# Security Keys for Duty Bot\n")
            f.write("# Generated by scripts/generate_security_keys.py\n")
            f.write("# DO NOT COMMIT THIS FILE TO VERSION CONTROL\n\n")

            for key, value in keys.items():
                f.write(f"{key}={value}\n")

        print(f"\n✅ Keys saved to: {filepath}")
        print(f"   Copy these values to your .env file")


def main():
    parser = argparse.ArgumentParser(
        description='Generate security keys for Duty Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate and display keys
  python scripts/generate_security_keys.py

  # Generate and save to file
  python scripts/generate_security_keys.py --output .env.security

  # Generate only encryption key
  python scripts/generate_security_keys.py --only-encryption

Security Best Practices:
  - Use different keys for development and production
  - Never commit keys to version control
  - Store keys securely (password manager, vault)
  - Rotate keys periodically
  - Keep backups of production keys in a secure location
        """
    )

    parser.add_argument(
        '--output', '-o',
        help='Save keys to specified file (e.g., .env.security)',
        metavar='FILE'
    )

    parser.add_argument(
        '--only-encryption',
        action='store_true',
        help='Generate only the encryption key (ENCRYPTION_KEY)'
    )

    parser.add_argument(
        '--no-explanation',
        action='store_true',
        help='Hide usage explanations in output'
    )

    args = parser.parse_args()

    generator = SecurityKeysGenerator()

    # Generate keys
    if args.only_encryption:
        keys = {'ENCRYPTION_KEY': generator.generate_encryption_key()}
    else:
        keys = generator.generate_all_keys()

    # Display keys
    generator.display_keys(keys, show_explanation=not args.no_explanation)

    # Save to file if requested
    if args.output:
        generator.save_to_file(keys, args.output)
        print("\n⚠️  Remember to:")
        print(f"   1. Copy keys from {args.output} to your .env file")
        print(f"   2. Delete {args.output} after copying (or store securely)")
        print(f"   3. Never commit {args.output} to version control")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
