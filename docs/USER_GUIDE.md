# User Guide

A tour of the Körüg web dashboard. Navigation is a left sidebar; the top bar has a light/dark theme toggle and your account menu (Profile, Logout).

## Logging in

Open the dashboard, sign in with your username and password. First-time admin credentials come from the server logs (see [Quick Start](QUICKSTART.md)). Change your password under **Profile**.

## Pages

### Dashboard
At-a-glance stat cards — total domains, vulnerabilities, active scans, high-risk domains — plus the **Monitored Domains** table. Each row has actions:
- **Run scan** ▶ — opens a dialog with an optional *Include port scan (active)* toggle, then starts the scan.
- **Stop scan** ■ — while a scan runs, the row shows a live **Scanning…** status and the Run button becomes a Stop button; clicking it cancels the in-progress scan (any results already found are kept).
- **View results** 👁 — opens the domain detail view.
- **Edit** ✏️ — rename the domain or enable/disable it (disabled domains are skipped by scheduled scans).
- **Delete** 🗑 — remove the domain and its results.

Add a domain with **Add Domain**.

### Assets
A single, searchable list of every subdomain discovered across **all** your domains — the full passive footprint, including names that don't currently resolve or have disappeared. Search by name and filter by **Live**, **Resolving**, or **Gone**; sort by host, domain, status, or last-seen. Each row is **clickable** and opens the subdomain detail view.

### Domain detail
Summary counts (subdomains / open issues / sources / risk) above a sortable, filterable table of every discovered subdomain — host, DNS records, source, and live/orphan/**gone** status. Search, sort by host or status, filter (All / Live / Issues / Gone), **rescan** the whole domain, and click any row to open its detail. 

### Subdomain detail
The per-host page (click any subdomain anywhere in the app). It shows status and key facts, full DNS records, HTTP fingerprint (status, server, technologies), open ports, the host's **vulnerabilities** (with false-positive flagging), its **certificates** from crt.sh (issuer, common name, validity, SANs), and a **change history** timeline. Use **Rescan host** to refresh enrichment + CVE/takeover checks, or **Refresh certs** to re-pull Certificate Transparency data.

### Changes
The attack-surface activity feed: every change the monitor has observed — subdomains appearing, disappearing, or reappearing; hosts going live/offline; IP, technology, and open-port shifts; and newly-issued certificates. Search by host, filter by change type, choose a time window (24h / 7d / 30d / all), and sort. Click a row to jump to the affected host.

### Vulnerabilities
Every finding across all domains in one sortable table — affected host, type, confidence, and when it was found. Search by host/domain, filter by type and by status (open / false positive / all), sort by any column, and flag/restore false positives in one click.

### Alerts
Security alerts are raised automatically whenever a scan finds a new vulnerability or observes a significant attack-surface change. Search, filter by severity, and sort by newest or severity.

### Users *(admin only)*
Create users, change roles (`admin` / `viewer`), enable/disable accounts, reset passwords, and delete users. You can't delete or demote yourself or the last admin.

### Integrations *(admin only)*
Configure **Slack** (incoming webhook) and **Email** (SMTP host/port/credentials, from/recipients). Toggle each on, **Save**, then **Send test** to confirm delivery. Stored secrets are masked — leave a secret field blank to keep the saved value.

### Settings
Your preferences (notifications, email alerts, theme, scan frequency, export format) and **API Keys** — generate a key (shown once), copy it, revoke or delete it. The theme control mirrors the top-bar light/dark toggle.

### Profile
View your account, update your email, and change your password (requires your current password).

### Audit Logs
A record of security-relevant actions (logins, domain and user changes, scans, exports, integration edits). You see your own activity; admins see everyone's.

## Running scans

Run a scan from the dashboard (**Run scan** ▶), the CLI (`korug scan --domain example.com`), the API (`POST /api/scans/{id}/scan`, add `?port_scan=true` to include a port scan), or the daily schedule (`SCAN_SCHEDULE_HOUR`/`MINUTE`). A running scan can be stopped from its dashboard row (**Stop** ■) or `POST /api/scans/{id}/scan/cancel`; cancellation is cooperative and keeps whatever was already found.

A scan: aggregates subdomains from all configured sources → resolves DNS and groups by IP → probes HTTP(S) (status/title/server, https→http fallback) → fingerprints technologies and flags Cloudflare → optionally port-scans → tests for takeover → diffs each host against its previous state and records changes → for new or changed live hosts, looks up CVEs (NVD) and pulls certificates (crt.sh) → flags any hosts that disappeared → stores results, raises alerts, and sends Slack/email notifications when enabled.

CVE and certificate steps run automatically only for new/changed live hosts (to stay within NVD/crt.sh rate limits); a manual **Rescan host** always runs them. Both can be disabled with `ENABLE_AUTO_CVE` / `ENABLE_CERT_MONITORING`.

> **Port scanning is active.** It's off by default and opt-in per scan — only enable it for targets you're authorized to scan.

## Vulnerability types

| Type | Typical confidence | Meaning |
|------|--------------------|---------|
| Subdomain takeover | 95% (70% edge) | CNAME points at a known service (GitHub Pages, Heroku, Shopify, Fastly, Ghost, …) **and** the target is dangling (NXDOMAIN) or its page matches the service's "unclaimed" fingerprint. Precise — needs both a CNAME match and a dangling/fingerprint signal |
| S3 bucket takeover | ~95% | CNAME points to an unclaimed S3 bucket (authoritative bucket-existence check) |
| CNAME orphan | ~85% | CNAME target doesn't resolve (generic; only when no specific service matched) |
| Orphaned NS record | ~85% | NS target doesn't exist |
| Orphaned MX record | ~80% | MX target doesn't exist |
| CVE (`cve:CVE-…`) | from CVSS | NVD keyword match on a host's fingerprinted product + version (best-effort; verify before acting) |

Only findings at or above the confidence threshold (default 75) raise alerts. Findings can be flagged as false positives via the API.
