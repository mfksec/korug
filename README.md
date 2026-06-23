<h1 align="center">𐰚𐰘𐰺𐰈𐰏 Körüg</h1>

<p align="center">
    Subdomain discovery and takeover vulnerability detection
</p>

# Overview

Körüg (Old Turkic for "protection/guardian") automates subdomain discovery and vulnerability detection. It discovers subdomains across multiple sources, detects takeover vulnerabilities, and integrates with Slack for real-time alerts.

# Features

- Multi-source subdomain discovery (Subfinder, Amass, Shodan, urlscan)
- Vulnerability detection (S3 bucket takeover, CNAME orphans, DNS orphans)
- REST API with Swagger documentation
- Web dashboard and CLI tool
- Slack notifications and scheduled scans
- XLSX export for reporting

# Installation

```bash
git clone https://github.com/mfksec/korug.git
cd korug
docker-compose -f docker/docker-compose.yml up -d
```

Dashboard: http://localhost:3000 | API: http://localhost:8000/docs

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