<h1 align="center">𐰚𐰘𐰺𐰈𐰏 Körüg</h1>

<p align="center">
    Subdomain discovery, takeover detection, and continuous monitoring
</p>

# Overview

Körüg (Old Turkic for "protection/guardian") automates subdomain discovery and takeover vulnerability detection. It enumerates subdomains across multiple sources, scores takeover risk, and surfaces findings through a web dashboard, REST API, and CLI — with Slack and email alerts when something needs attention.

All dashboards reflect real scan data: charts, alerts, and statistics are computed from your own scans, not seeded samples.

# Features

**Passive discovery**
- Aggregates subdomains from many free, no-key sources — crt.sh, HackerTarget, CertSpotter, RapidDNS, AlienVault OTX, ThreatMiner, Wayback, BufferOver, ThreatCrowd
- Optional key-gated sources: VirusTotal, SecurityTrails, BinaryEdge, Censys, urlscan, Shodan; plus local Subfinder (Amass opt-in via `ENABLE_AMASS`)
- Per-source attribution; every source is best-effort so one failure never fails a scan

**Enrichment & detection**
- DNS resolution to IPs, with subdomains classified by shared IP
- HTTP(S) probing with smart https→http fallback: status code, final URL, title, content-length, server
- Technology fingerprinting and Cloudflare detection
- Optional port scan (nmap with service/version when available, else built-in TCP scan)
- Subdomain takeover detection — unclaimed S3 buckets, orphaned CNAME / MX / NS — with per-finding confidence scoring

**Dashboard**
- Redesigned React UI with a sidebar app shell and light/dark mode
- Add, edit, and scan domains; per-scan opt-in port scanning
- Live scan status with a Stop button — cancel an in-progress scan at any time
- Assets page: a searchable, filterable list of every detected subdomain across all domains
- Domain detail view: subdomains, IPs (grouped), HTTP/title/server, technologies, open ports, Cloudflare, vulnerabilities
- Real-time analytics: 30-day discovery trend, severity distribution, and findings by type

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
cp docker/.env.docker docker/.env   # Docker config; set JWT_SECRET_KEY, API_KEY, DB credentials
docker compose -f docker/docker-compose.yml up -d --build
```

> Use `--build` (and `--build` again when updating) so Docker doesn't reuse a stale cached image.

Dashboard: http://localhost:3000 | API docs: http://localhost:8000/docs

On first run an initial `admin` account is created. If `ADMIN_PASSWORD` is not set, a strong random password is generated and printed to the logs once — capture it and change it after logging in.

> Configure secrets via environment variables, never in committed files. See [.env.example](.env.example) for all options. Slack and email notifications are configured at runtime from the dashboard's **Integrations** page.

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
