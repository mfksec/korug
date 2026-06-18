# Security Policy

## Reporting Security Vulnerabilities

**Do not** open a public GitHub issue for security vulnerabilities.

Instead, please email security@amboss.com with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

We will acknowledge your report within 48 hours and provide a detailed response within 5 days.

## Security Best Practices

### API Key Management
- Never commit API keys to the repository
- Use environment variables for all secrets
- Rotate keys regularly
- Use strong, random keys (minimum 32 characters)

### Database Security
- Always use strong passwords (minimum 16 characters)
- Enable SSL for database connections in production
- Use network isolation and firewalls
- Regular backups with encryption

### Deployment Security
- Use HTTPS/TLS for all communications
- Keep dependencies updated regularly
- Run security scans (e.g., Snyk, OWASP)
- Use non-root users in Docker containers

### Subdomain Scanning Safety
- Respect robots.txt and Terms of Service
- Avoid aggressive scanning of third-party domains
- Scan only domains you own or have permission to test
- Rate limiting to avoid DoS triggers

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Known Issues

None currently documented.

## Security Updates

Security updates will be released as patch versions (e.g., 0.1.1) and announced in the GitHub releases.

Subscribe to releases to be notified of security updates:
1. Go to the repository
2. Click "Watch" → "Custom"
3. Check "Releases"

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
