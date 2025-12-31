#!/usr/bin/env python3
"""
Environment Configuration Validator

This script validates that all required environment variables are properly
configured for running Duty Bot. It checks for required variables, suggests
values for missing ones, and provides helpful error messages.

Usage:
    python scripts/validate_env.py
    # or via Make:
    make env-check
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional


class Colors:
    """ANSI color codes for terminal output"""
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color


def print_header(text: str) -> None:
    """Print a section header"""
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.NC}")
    print(f"{Colors.BLUE}{text:^70}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.NC}\n")


def print_success(text: str) -> None:
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")


def print_warning(text: str) -> None:
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")


def print_error(text: str) -> None:
    """Print an error message"""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")


def load_env_file(filepath: Path) -> Dict[str, str]:
    """Load environment variables from a file"""
    env_vars = {}

    if not filepath.exists():
        return env_vars

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line.startswith('#') or not line:
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print_error(f"Failed to read {filepath}: {e}")

    return env_vars


def validate_required_vars(env_vars: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate that all required environment variables are set

    Returns:
        Tuple of (is_valid, list_of_missing_vars)
    """
    required_vars = {
        # Database
        'DATABASE_URL': 'PostgreSQL connection string',
        'POSTGRES_DB': 'PostgreSQL database name',
        'POSTGRES_USER': 'PostgreSQL username',
        'POSTGRES_PASSWORD': 'PostgreSQL password',

        # Application
        'ENCRYPTION_KEY': 'Key for encrypting sensitive data',
        'SECRET_KEY': 'General application secret',
        'SESSION_SECRET': 'Session cookie secret',
        'API_TOKEN': 'API token for internal access',

        # Server
        'HOST': 'Server host (0.0.0.0 for all interfaces)',
        'PORT': 'Server port',
        'ENVIRONMENT': 'Environment (development/staging/production)',
    }

    missing_vars = []

    for var, description in required_vars.items():
        value = env_vars.get(var, os.environ.get(var, ''))

        # Check if variable is missing or contains placeholder
        if not value or value in ['generate_with_python_command', 'your_*']:
            missing_vars.append(f"{var:<20} - {description}")

    is_valid = len(missing_vars) == 0
    return is_valid, missing_vars


def validate_optional_vars(env_vars: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate optional but recommended environment variables

    Returns:
        Tuple of (all_recommended_set, list_of_missing_vars)
    """
    optional_vars = {
        # Telegram
        'TELEGRAM_TOKEN': 'Telegram bot token (from @BotFather)',
        'TELEGRAM_CHAT_ID': 'Telegram chat ID for messages',

        # Slack
        'SLACK_BOT_TOKEN': 'Slack bot token (starts with xoxb-)',
        'SLACK_SIGNING_SECRET': 'Slack signing secret for webhooks',
        'SLACK_CLIENT_ID': 'Slack OAuth client ID',
        'SLACK_CLIENT_SECRET': 'Slack OAuth client secret',

        # Settings
        'TIMEZONE': 'Timezone for scheduled tasks',
        'MORNING_DIGEST_TIME': 'Time for morning digest (HH:MM)',
        'ESCALATION_TIMEOUT_MINUTES': 'Minutes before auto-escalation',
    }

    missing_vars = []

    for var, description in optional_vars.items():
        value = env_vars.get(var, os.environ.get(var, ''))

        if not value or value.startswith('your_'):
            missing_vars.append(f"{var:<25} - {description}")

    all_set = len(missing_vars) == 0
    return all_set, missing_vars


def check_security_keys(env_vars: Dict[str, str]) -> Tuple[bool, List[str]]:
    """Check security-related configuration"""
    issues = []

    # Check encryption key format
    encryption_key = env_vars.get('ENCRYPTION_KEY', os.environ.get('ENCRYPTION_KEY', ''))
    if encryption_key:
        try:
            import base64
            base64.b64decode(encryption_key)
        except Exception:
            issues.append("ENCRYPTION_KEY is not a valid base64-encoded string")

    # Check if CORS is configured for production
    environment = env_vars.get('ENVIRONMENT', os.environ.get('ENVIRONMENT', ''))
    cors_origins = env_vars.get('CORS_ORIGINS', os.environ.get('CORS_ORIGINS', ''))

    if environment == 'production' and not cors_origins:
        issues.append("CORS_ORIGINS not set for production environment (security risk)")

    return len(issues) == 0, issues


def check_external_services(env_vars: Dict[str, str]) -> Dict[str, bool]:
    """Check which external services are configured"""
    services = {
        'telegram': bool(env_vars.get('TELEGRAM_TOKEN', os.environ.get('TELEGRAM_TOKEN', ''))),
        'slack': bool(env_vars.get('SLACK_BOT_TOKEN', os.environ.get('SLACK_BOT_TOKEN', ''))),
    }

    return services


def validate_database_connection(env_vars: Dict[str, str]) -> Tuple[bool, Optional[str]]:
    """Try to validate database connection URL format"""
    db_url = env_vars.get('DATABASE_URL', os.environ.get('DATABASE_URL', ''))

    if not db_url:
        return False, "DATABASE_URL not set"

    # Check for proper format
    if not db_url.startswith('postgresql'):
        return False, "DATABASE_URL doesn't start with 'postgresql'"

    if not '://' in db_url:
        return False, "DATABASE_URL missing connection prefix (postgresql://)"

    return True, None


def main():
    """Main validation function"""

    print_header("Duty Bot - Environment Configuration Validator")

    # Determine env file to check
    env_files = [
        Path('.env'),
        Path('.env.local'),
    ]

    env_vars: Dict[str, str] = {}
    found_env_file = None

    for env_file in env_files:
        if env_file.exists():
            env_vars.update(load_env_file(env_file))
            found_env_file = env_file
            print_success(f"Loaded configuration from {env_file}")

    # Merge with OS environment variables
    env_vars.update(os.environ)

    if not found_env_file:
        print_warning("No .env file found. Using OS environment variables only.")

    # Validate required variables
    print_header("Required Configuration")
    required_valid, required_missing = validate_required_vars(env_vars)

    if required_valid:
        print_success("All required configuration variables are set!")
    else:
        print_error("Missing required configuration variables:")
        for var in required_missing:
            print(f"  - {var}")

    # Validate optional variables
    print_header("Optional Configuration (Recommended)")
    optional_valid, optional_missing = validate_optional_vars(env_vars)

    if optional_valid:
        print_success("All recommended optional variables are configured!")
    else:
        print_warning("The following optional variables are not configured:")
        for var in optional_missing:
            print(f"  - {var}")

    # Check external services
    print_header("External Services Configuration")
    services = check_external_services(env_vars)

    for service, configured in services.items():
        if configured:
            print_success(f"{service.capitalize()} is configured")
        else:
            print_warning(f"{service.capitalize()} is not configured (optional)")

    # Check security configuration
    print_header("Security Configuration")
    security_valid, security_issues = check_security_keys(env_vars)

    if security_valid:
        print_success("Security configuration looks good")
    else:
        for issue in security_issues:
            print_warning(issue)

    # Check database connection
    print_header("Database Configuration")
    db_valid, db_error = validate_database_connection(env_vars)

    if db_valid:
        print_success("Database URL format is valid")
        db_url = env_vars.get('DATABASE_URL', os.environ.get('DATABASE_URL', ''))
        # Show masked connection string
        masked_url = db_url.replace(
            env_vars.get('POSTGRES_PASSWORD', os.environ.get('POSTGRES_PASSWORD', 'password')),
            '***'
        )
        print(f"  Connection: {masked_url}")
    else:
        print_error(f"Database URL validation failed: {db_error}")

    # Summary
    print_header("Validation Summary")

    if required_valid and security_valid and db_valid:
        print_success("✓ All critical configuration is valid!")
        print("You're ready to start the application.")
        return 0
    else:
        print_error("✗ Some configuration issues need to be fixed before running the application.")
        print("\nTo fix configuration:")
        print("  1. Edit .env file (or create it from .env.example)")
        print("  2. Run: python scripts/validate_env.py")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nValidation cancelled.")
        sys.exit(130)
    except Exception as e:
        print_error(f"Validation error: {e}")
        sys.exit(1)
