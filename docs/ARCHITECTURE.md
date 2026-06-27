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
- **takeover_detection.py** — scores takeover risk. The precise check (modelled on `can-i-take-over-xyz`, fingerprints in **takeover_fingerprints.py**) flags a host when its CNAME points at a known service (GitHub Pages, Heroku, Shopify, Fastly, …) **and** the target is dangling (NXDOMAIN) or the HTTP body matches the service's "unclaimed" fingerprint. Plus unclaimed S3 buckets (boto3), generic orphaned CNAME, and orphaned MX/NS (dnspython). Each finding gets a 0–100 confidence.
- **cve.py** — best-effort CVE lookup against the public NVD API by product+version keyword, with an in-process TTL cache and rate-limit-aware pacing (an NVD key raises the limit).
- **nuclei.py** — active, template-based scanning via the nuclei CLI (takeover/CVE/exposure/misconfiguration/default-login). Opt-in (`ENABLE_NUCLEI`), active-mode only, run once per scan over the incremental alive host set; best-effort. Findings stored as `nuclei:<template-id>`.
- **certstream_monitor.py** — opt-in (`ENABLE_CERTSTREAM`) background consumer of a certstream CT feed; new subdomains of monitored domains are recorded as assets + `subdomain_added` changes in near real-time. Self-healing (reconnect with backoff).
- **certificates.py** — Certificate Transparency lookup via crt.sh (issuer, CN, SANs, serial, validity), de-duplicated by serial, cached in-process.
- **changes.py** — attack-surface change detection: pure `diff_subdomain()` plus `record_changes()`, which persists `AssetChange` rows and raises `Alert`s for the significant ones.
- **slack_integration.py** — posts alerts/summaries to a Slack webhook.
- **email_integration.py** — sends alerts/test mail over SMTP (stateless; config passed in).

## Data models (`src/korug/models/base.py`)

| Model | Purpose |
|-------|---------|
| `User` | Accounts, roles, password hash |
| `Domain` | A monitored domain |
| `Subdomain` | Discovered subdomain + DNS records, sources, and enrichment (IPs, HTTP status/title/server, technologies, open ports, Cloudflare); `is_gone`/`gone_at` flag names that disappeared |
| `Vulnerability` | Finding with type, confidence, false-positive flag |
| `Certificate` | TLS certificate observed for a subdomain (issuer, CN, SANs, serial, validity), sourced from crt.sh |
| `AssetChange` | The attack-surface change log: one row per observed change (added/removed/live/offline/IP/tech/ports/new-cert) |
| `ScanHistory` | Per-scan stats and status |
| `Alert` | Alert raised from a finding (resolvable) |
| `ApiKey` | Hashed API keys (masked display) |
| `UserSetting` | Per-user preferences |
| `AuditLog` | Persistent security-event log |
| `IntegrationConfig` | Slack/email config (secrets stored, masked on read) |

## API layer (`src/korug/api/`)

`domains`, `scans`, `changes`, `vulnerabilities`, `alerts`, `users`, `integrations`, `settings`, `export` — plus auth routes in `main.py`. Auth is enforced by a `get_current_user` dependency; admin-only routes use `require_role("admin")`. Audit events are written through `audit.py`.

## Scan flow

```
trigger (dashboard / CLI / API / scheduler)
  → discovery: aggregate names from all configured sources (concurrent)
  → enrichment: resolve DNS → group by IP → HTTP(S) probe → tech + Cloudflare
                → optional port scan
     (passive monitor_mode skips the HTTP probe + ports → DNS-only, low-touch)
  → upsert ALL discovered subdomains with their enrichment
  → diff each host vs its prior state → record AssetChange + alerts
  → takeover detection per subdomain
  → incremental pass (new/changed alive hosts only): CVE lookup + crt.sh certs
  → mark disappeared names is_gone (record subdomain_removed once)
  → store vulnerabilities, raise Alerts for new findings
  → notify Slack / email (if enabled)
  → record ScanHistory
```

The scheduler (`scheduler.py`, APScheduler) re-runs this for every enabled domain
daily at the configured time — the continuous-monitoring loop. CVE and certificate
work is gated to the incremental set (and to `ENABLE_AUTO_CVE` / `ENABLE_CERT_MONITORING`)
so repeated scans stay fast and within NVD/crt.sh rate limits.

## Attack-surface monitoring roadmap

Built: per-host detail views, certificate transparency monitoring, automatic
incremental vulnerability scanning, the asset change-log with change alerts,
per-domain active/passive monitoring mode, active template scanning (nuclei), and
live CT-log streaming (certstream).
Planned next: ownership-confidence + scope allowlist gating for the active tools
(Phase 2); per-domain scan cadence; routing change-alerts through the existing
Slack/email integrations; exposure-over-time trend dashboards; port/service & tech
drift views; IP/ASN grouping; exportable ASM reports; finding aging/SLA; and
adopting Alembic for real migrations (today new columns are added best-effort at
startup by `db._add_missing_columns`).

## Stack

FastAPI · SQLAlchemy · PostgreSQL · Redis (optional) · Click (CLI) · APScheduler · aiohttp · dnspython · boto3 · nmap + defusedxml (port scan) · openpyxl (XLSX) · React + Vite + MUI + Recharts · JWT (bcrypt password hashing) · Docker.

## Security notes

JWT with token revocation; bcrypt password hashing; role-based access; API-key and audit-log secrets stored hashed/masked; CORS restricted via `ALLOWED_ORIGINS`; login rate limiting; no stack traces in API responses. See [Authentication & Users](AUTH.md) and the [Security Policy](../SECURITY.md).
