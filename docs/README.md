# Overview

This directory contains the core documentation for Subdomain Hunter.

## Getting Started

1. **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
2. **[Installation Guide](INSTALLATION.md)** - Detailed setup instructions
3. **[Authentication & Users](AUTH.md)** - Login, user management, security

## Using Subdomain Hunter

- **[User Guide](USER_GUIDE.md)** - Dashboard features and workflows
- **[API Reference](API.md)** - REST API endpoints with examples
- **[CLI Reference](CLI.md)** - Command-line tool documentation
- **[Architecture](ARCHITECTURE.md)** - System design and components

## Security & Operations

- **[Security Policy](../SECURITY.md)** - Reporting vulnerabilities & best practices
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute
- **[Changelog](../CHANGELOG.md)** - Release history

## Key Concepts

### Authentication
Two authentication methods supported:
- **User JWT Tokens**: Login with username/password for dashboard and API access
- **API Keys**: Service-to-service authentication for scripts and integrations
- See [Authentication & Users](AUTH.md) for complete details

### Discovery Process
Subdomains are discovered using multiple passive sources:
- Subfinder & Amass (local tools)
- Shodan.io & urlscan.io APIs (optional)

### Vulnerability Types
Three main vulnerability types detected:
1. **S3 Bucket Takeover** - CNAME to unclaimed S3 bucket
2. **CNAME Orphan** - CNAME target doesn't exist
3. **DNS Orphans** - MX/NS records pointing to missing servers

### Confidence Scoring
All findings include a confidence score (0-100%). Only findings ≥75% (configurable) trigger alerts.

## Recommended Reading Order

1. Start with [Quick Start](INSTALLATION.md#quick-start)
2. Review [API Reference](API.md) or [CLI Reference](CLI.md) depending on your usage
3. Explore [Architecture](ARCHITECTURE.md) for understanding the system
4. Check [Contributing](../CONTRIBUTING.md) if you want to help

## FAQ

**Q: Can I run this without Shodan/urlscan APIs?**
A: Yes! The tool falls back to free Subfinder/Amass sources.

**Q: How often can I scan?**
A: Scan frequency is configurable via cron or APScheduler (default: daily).

**Q: Does this scan third-party domains?**
A: Only domains you add. Always ensure you have permission before scanning.

**Q: Can I export results?**
A: Yes, XLSX export includes all subdomains and vulnerabilities.

## Troubleshooting

See [Installation Guide](INSTALLATION.md#troubleshooting) for common issues.
