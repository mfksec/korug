<h1 align="center">𐰚𐰘𐰺𐰈𐰏 Körüg</h1>

<p align="center">
    Subdomain discovery, takeover detection, and continuous monitoring
</p>

# Overview

Körüg (Old Turkic for "protection/guardian") automates subdomain discovery and takeover vulnerability detection. It enumerates subdomains across multiple sources, scores takeover risk, and surfaces findings through a web dashboard, REST API, and CLI — with Slack and email alerts when something needs attention.

All dashboards reflect real scan data: charts, alerts, and statistics are computed from your own scans, not seeded samples.

# Features

**Discovery & detection**
- Multi-source subdomain discovery (Subfinder, Amass, Shodan, urlscan)
- Takeover detection — unclaimed S3 buckets, orphaned CNAME / MX / NS records — with per-finding confidence scoring

**Dashboard**
- Redesigned React UI with a sidebar app shell and light/dark mode
- Real-time analytics: 30-day discovery trend, severity distribution, and findings by type
- Per-domain scan history and results

**Alerts & notifications**
- In-app security alerts raised automatically from scan findings
- Slack and Email (SMTP) integrations — configurable and testable directly from the UI

**Access control & administration**
- JWT authentication with `admin` / `viewer` roles
- User management: create users, change roles, enable/disable, reset passwords
- Self-service profile and password changes
- API keys for programmatic access
- Persistent audit log of security-relevant actions

**Automation & reporting**
- Scheduled scans
- REST API with Swagger documentation and a companion CLI
- CSV / JSON / XLSX export

# Installation

```bash
git clone https://github.com/mfksec/korug.git
cd korug
cp .env.example .env        # set DATABASE_URL, JWT_SECRET_KEY, API_KEY, ALLOWED_ORIGINS
docker compose -f docker/docker-compose.yml up -d
```

Dashboard: http://localhost:3000 | API docs: http://localhost:8000/docs


# Documentation

- [Quick Start](docs/QUICKSTART.md)
- [User Guide](docs/USER_GUIDE.md)
- [API Reference](docs/API.md)
- [CLI Reference](docs/CLI.md)
- [Authentication](docs/AUTH.md)
- [Architecture](docs/ARCHITECTURE.md)

<p align="center">
    <a href="LICENSE">
        <img src="https://img.shields.io/github/license/mfksec/korug?style=flat-square" />
    </a>
    <a href="https://github.com/mfksec/korug">
        <img src="https://img.shields.io/github/stars/mfksec/korug?style=social" />
    </a>
</p>
