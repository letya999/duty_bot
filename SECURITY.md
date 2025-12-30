# Security Policy

## Security Responsibilities

Duty Bot handles sensitive IT infrastructure data including duty schedules, escalation procedures, and integration credentials. Security is a top priority for this project.

## Supported Versions

We provide security updates for the following versions:

| Version | Status | Security Updates |
|---------|--------|------------------|
| 2.x | Current | ✅ Yes |
| 1.x | Legacy | ⚠️ Limited support |
| 0.x | Deprecated | ❌ No |

## Reporting Security Vulnerabilities

**DO NOT open public issues for security vulnerabilities.**

If you discover a security vulnerability, please report it responsibly:

1. **Email**: Send details to the project maintainers (check GitHub repository for contact info)
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

3. **Response time**: We aim to acknowledge receipt within 48 hours

Please allow reasonable time for the maintainers to:
- Investigate and confirm the vulnerability
- Develop and test a fix
- Prepare a security release
- Notify users

We will credit security researchers who report vulnerabilities responsibly.

## Security Measures

### Authentication & Authorization

- **OAuth2 support** for admin panel access
- **Session management** with encrypted session tokens
- **CSRF protection** on state-changing operations
- **Role-based access control** (admin/user levels)

### Data Protection

- **Encryption at rest**: Sensitive data encrypted in database
- **Encryption in transit**: HTTPS/TLS recommended for deployment
- **Password hashing**: Secure hashing for any stored credentials
- **Secret management**: Use environment variables, never hardcode secrets

### API Security

- **Rate limiting** to prevent abuse
- **Security headers** (CSP, X-Frame-Options, etc.)
- **Input validation** on all endpoints
- **SQL injection prevention** via parameterized queries (SQLAlchemy ORM)
- **XSS prevention** via proper escaping

### Third-Party Integrations

- **Telegram Bot API**: Uses official HTTPS endpoints
- **Slack Bot API**: Verifies request signatures
- **Google Calendar**: OAuth2 with proper scope restrictions

## Security Best Practices for Users

### Deployment

1. **Use HTTPS/TLS** in production
2. **Secure database credentials** - use strong passwords, don't expose in logs
3. **Rotate encryption keys** regularly
4. **Keep dependencies updated** - run `pip install --upgrade -r requirements.txt`
5. **Use environment variables** for all secrets
6. **Restrict database access** - use firewall rules
7. **Enable bot rate limiting** - configured via environment variables

### Configuration

- **ENCRYPTION_KEY**: Keep this secure and unique per deployment
- **Database credentials**: Use strong, randomly generated passwords
- **Bot tokens**: Never share or commit these
- **OAuth secrets**: Treat as sensitive credentials
- **Admin IDs**: Restrict to authorized users only

### Monitoring

- Monitor logs for suspicious activity
- Set up alerts for failed authentication attempts
- Review admin action logs regularly
- Monitor bot usage patterns

## Known Limitations

- Slack workspace isolation depends on proper workspace configuration
- Telegram group privacy depends on group settings
- Google Calendar sync respects Google Calendar permissions
- No built-in rate limiting at the database level (use application-level limits)

## Dependency Security

We use:
- **Python**: FastAPI, SQLAlchemy, cryptography, and other established libraries
- **JavaScript/React**: React, Axios, Tailwind CSS, and other trusted packages
- **CI/CD**: Regular dependency updates and security scanning (recommended)

### Checking Dependencies

```bash
# Python
pip install safety
safety check

# JavaScript
npm audit
npm audit fix
```

## Security Incident Response

If a security vulnerability is discovered:

1. Developers will create a fix in private
2. A patch release will be published with minimal disclosure
3. Users will be notified and encouraged to update
4. Security advisory will be posted after sufficient time for patching

## Future Security Improvements

- [ ] Automated dependency scanning
- [ ] Security headers hardening
- [ ] Two-factor authentication for admin panel
- [ ] Audit logging enhancements
- [ ] Penetration testing results documentation

## Compliance

This project aims to follow:
- OWASP Top 10 security principles
- OAuth 2.0 best practices
- Secure coding guidelines

## Questions?

For security-related questions or concerns:
- Review this policy
- Check existing documentation
- Contact maintainers via private channels

---

**Last Updated**: December 2024

Thank you for helping keep Duty Bot secure!
