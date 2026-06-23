# Documentation

Core documentation for Körüg.

| Doc | What's in it |
|-----|--------------|
| [Quick Start](QUICKSTART.md) | Run Körüg with Docker in a few minutes |
| [Installation](INSTALLATION.md) | Docker and local-dev setup, environment variables |
| [User Guide](USER_GUIDE.md) | The web dashboard, page by page |
| [Authentication & Users](AUTH.md) | Login, roles, user management, API keys |
| [API Reference](API.md) | REST endpoints (Swagger lives at `/docs`) |
| [CLI Reference](CLI.md) | Command-line tool |
| [Architecture](ARCHITECTURE.md) | Components, data model, data flow |

Also: [Security Policy](../SECURITY.md) · [Contributing](../CONTRIBUTING.md) · [Changelog](../CHANGELOG.md)

## Concepts in one minute

- **Discovery** — subdomains are enumerated from Subfinder, Amass, and (optionally) Shodan and urlscan.
- **Detection** — each subdomain is checked for takeover risk: unclaimed S3 buckets and orphaned CNAME / MX / NS records.
- **Confidence** — every finding gets a 0–100 score; only findings at or above the threshold (default 75) raise alerts.
- **Alerts** — findings surface in the dashboard and can be pushed to Slack and email.
- **Access** — JWT auth with `admin` and `viewer` roles; API keys for scripts.

## FAQ

**Run without Shodan/urlscan keys?** Yes — it falls back to Subfinder/Amass.
**Trigger scans?** Via the CLI (`korug scan`), the API, or the daily scheduler. Add/remove domains in the dashboard.
**Scan third-party domains?** Only domains you add — make sure you're authorized.
