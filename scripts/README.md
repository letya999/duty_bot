# Duty Bot Scripts

Utility scripts for administration and security configuration.

**Documentation:**
- [SETUP_GUIDE.md](../docs/SETUP_GUIDE.md) - Service configuration (Slack, Google Calendar, Telegram)
- [COMMANDS.md](../docs/COMMANDS.md) - Complete command reference
- [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) - Solutions for common issues

---

## Security Keys Generator

Generate cryptographic keys for secure data encryption and session management.

### Quick Start

```bash
# Generate all keys and display
python scripts/generate_security_keys.py

# Generate and save to file
python scripts/generate_security_keys.py --output .env.security

# Then copy to .env and securely delete the temp file
cat .env.security >> .env
shred -u .env.security  # Linux
rm -P .env.security     # macOS
```

### What Gets Generated

| Key | Purpose | Required |
|-----|---------|----------|
| `ENCRYPTION_KEY` | Encrypts sensitive data (Google Calendar credentials) | **Yes** |
| `SECRET_KEY` | General application security (sessions, CSRF) | Yes |
| `SESSION_SECRET` | Signs session cookies | Yes |
| `API_TOKEN` | External API authentication | Optional |

### Command Options

```bash
--output FILE           Save keys to file instead of display
--only-encryption       Generate only ENCRYPTION_KEY
--no-explanation        Omit usage explanations in output
```

### Security Requirements

- **Never commit** `.env*` files to git (add to `.gitignore`)
- **Never share** keys publicly or in logs
- **Use different keys** for development and production
- **Rotate keys** every 6-12 months
- **Store securely** in password manager or secrets vault

### Troubleshooting

**"cryptography library not installed"**
```bash
pip install cryptography
```

**Regenerate single key**
```bash
python scripts/generate_security_keys.py --only-encryption
```

### Production Deployment

Store keys in a secrets management service:

**AWS Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name duty-bot/encryption-key \
  --secret-string "$(python scripts/generate_security_keys.py --only-encryption --no-explanation | grep ENCRYPTION_KEY | cut -d'=' -f2)"
```

**Docker Secrets:**
```bash
python scripts/generate_security_keys.py --only-encryption --no-explanation | \
  grep ENCRYPTION_KEY | cut -d'=' -f2 | \
  docker secret create duty_bot_encryption_key -
```

**Kubernetes:**
```bash
kubectl create secret generic duty-bot-secrets \
  --from-literal=encryption-key="$(python scripts/generate_security_keys.py --only-encryption --no-explanation | grep ENCRYPTION_KEY | cut -d'=' -f2)"
```
