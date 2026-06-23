# Architecture

## Overview

```
React + MUI dashboard ──┐
CLI (Click) ────────────┼──▶ FastAPI (REST API, JWT auth)
HTTP clients / API key ─┘            │
                                     ▼
            Services: discovery · takeover detection · slack · email
                                     │
                         SQLAlchemy ORM models
                                     ▼
                    PostgreSQL  (+ Redis, optional)
```

The frontend is a single-page React/Vite app (MUI + Recharts). The backend is FastAPI with SQLAlchemy; tables are created on startup via `Base.metadata.create_all` (no migration tool). PostgreSQL is the datastore; Redis is optional for distributed rate limiting and token revocation.

## Services (`src/korug/services/`)

- **discovery.py** — aggregates subdomains concurrently from many free web sources (crt.sh, HackerTarget, CertSpotter, RapidDNS, AlienVault OTX, ThreatMiner, Wayback, BufferOver, ThreatCrowd), key-gated providers (VirusTotal, SecurityTrails, BinaryEdge, Censys, urlscan, Shodan), and local Subfinder/Amass. Per-source attribution; best-effort.
- **enrichment.py** — concurrent DNS resolution, HTTP(S) probing (status/title/server, https→http fallback), technology fingerprinting, Cloudflare IP-range detection, and an optional port scan (nmap with `-sV` when available, else an async TCP connect scan; nmap XML parsed with defusedxml).
- **takeover_detection.py** — scores takeover risk: unclaimed S3 buckets (boto3), orphaned CNAME, and orphaned MX/NS (dnspython). Each finding gets a 0–100 confidence.
- **slack_integration.py** — posts alerts/summaries to a Slack webhook.
- **email_integration.py** — sends alerts/test mail over SMTP (stateless; config passed in).

## Data models (`src/korug/models/base.py`)

| Model | Purpose |
|-------|---------|
| `User` | Accounts, roles, password hash |
| `Domain` | A monitored domain |
| `Subdomain` | Discovered subdomain + DNS records, sources, and enrichment (IPs, HTTP status/title/server, technologies, open ports, Cloudflare) |
| `Vulnerability` | Finding with type, confidence, false-positive flag |
| `ScanHistory` | Per-scan stats and status |
| `Alert` | Alert raised from a finding (resolvable) |
| `ApiKey` | Hashed API keys (masked display) |
| `UserSetting` | Per-user preferences |
| `AuditLog` | Persistent security-event log |
| `IntegrationConfig` | Slack/email config (secrets stored, masked on read) |

## API layer (`src/korug/api/`)

`domains`, `scans`, `vulnerabilities`, `alerts`, `users`, `integrations`, `settings`, `export` — plus auth routes in `main.py`. Auth is enforced by a `get_current_user` dependency; admin-only routes use `require_role("admin")`. Audit events are written through `audit.py`.

## Scan flow

```
trigger (dashboard / CLI / API / scheduler)
  → discovery: aggregate names from all configured sources (concurrent)
  → enrichment: resolve DNS → group by IP → HTTP(S) probe → tech + Cloudflare
                → optional port scan
  → upsert resolvable subdomains with their enrichment
  → takeover detection per subdomain
  → store vulnerabilities, raise Alerts for new findings
  → notify Slack / email (if enabled)
  → record ScanHistory
```

The scheduler (`scheduler.py`, APScheduler) runs scans daily at the configured time.

## Stack

FastAPI · SQLAlchemy · PostgreSQL · Redis (optional) · Click (CLI) · APScheduler · aiohttp · dnspython · boto3 · nmap + defusedxml (port scan) · openpyxl (XLSX) · React + Vite + MUI + Recharts · JWT (bcrypt password hashing) · Docker.

## Security notes

JWT with token revocation; bcrypt password hashing; role-based access; API-key and audit-log secrets stored hashed/masked; CORS restricted via `ALLOWED_ORIGINS`; login rate limiting; no stack traces in API responses. See [Authentication & Users](AUTH.md) and the [Security Policy](../SECURITY.md).
