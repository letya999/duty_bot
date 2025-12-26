# Scripts

Utility scripts for Duty Bot administration and security.

## Security Keys Generator

Generate all required cryptographic keys for secure operation.

### Usage

```bash
# Generate all keys and display them
python scripts/generate_security_keys.py

# Generate and save to file
python scripts/generate_security_keys.py --output .env.security

# Generate only encryption key
python scripts/generate_security_keys.py --only-encryption
```

### Generated Keys

| Key | Purpose | Required |
|-----|---------|----------|
| `ENCRYPTION_KEY` | Encrypts Google Calendar credentials in database | Yes |
| `SECRET_KEY` | General application security | Recommended |
| `SESSION_SECRET` | Signs session cookies | Recommended |
| `API_TOKEN` | External API authentication | Optional |

### Security Best Practices

1. **Never commit keys to version control**
   - Add `.env*` to `.gitignore`
   - Use different keys for dev/staging/production

2. **Store keys securely**
   - Use a password manager
   - Use secrets management service (AWS Secrets Manager, Vault)
   - Keep encrypted backups

3. **Rotate keys periodically**
   - Every 6-12 months minimum
   - Immediately if compromised
   - After team member departures

4. **Key separation**
   - Use different keys for each environment
   - Use different keys for each application instance
   - Never reuse keys across projects

### Quick Start

```bash
# 1. Generate keys
python scripts/generate_security_keys.py --output .env.security

# 2. Copy to your .env file
cat .env.security >> .env

# 3. Securely delete the temporary file
shred -u .env.security  # Linux
# or
rm -P .env.security     # macOS
# or just delete manually and empty trash

# 4. Verify keys are set
grep ENCRYPTION_KEY .env
```

### Troubleshooting

**Error: cryptography library not installed**
```bash
pip install cryptography
```

**Need to regenerate a single key?**
```bash
# Generate only encryption key
python scripts/generate_security_keys.py --only-encryption

# Or use Python directly
python -c "from cryptography.fernet import Fernet; print(f'ENCRYPTION_KEY={Fernet.generate_key().decode()}')"
```

### Production Deployment

For production, use a secrets management service:

**AWS Secrets Manager:**
```bash
# Store encryption key
aws secretsmanager create-secret \
  --name duty-bot/encryption-key \
  --secret-string "$(python scripts/generate_security_keys.py --only-encryption --no-explanation | grep ENCRYPTION_KEY | cut -d'=' -f2)"
```

**Docker Secrets:**
```bash
# Create Docker secret
python scripts/generate_security_keys.py --only-encryption --no-explanation | \
  grep ENCRYPTION_KEY | cut -d'=' -f2 | \
  docker secret create duty_bot_encryption_key -
```

**Kubernetes Secrets:**
```bash
# Create Kubernetes secret
kubectl create secret generic duty-bot-secrets \
  --from-literal=encryption-key="$(python scripts/generate_security_keys.py --only-encryption --no-explanation | grep ENCRYPTION_KEY | cut -d'=' -f2)"
```
