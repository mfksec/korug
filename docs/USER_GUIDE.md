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
A single, searchable list of every subdomain discovered across **all** your domains — the full passive footprint, including names that don't currently resolve. Search by name and filter by **Resolves** or **Alive**. Each row shows the parent domain, resolved IP(s), HTTP status, title/server, technologies, and the sources that found it (e.g. crt.sh, subfinder). Run a scan from the Dashboard, then check here to see results.

**Domain detail** shows summary counts (subdomains / alive / vulnerabilities / Cloudflare) and three tabs: **Subdomains** (resolved IPs, HTTP status, title/server, technology chips, open ports with service/version, a Cloudflare badge, and a clickable live URL), **By IP** (subdomains grouped by shared address), and **Vulnerabilities**.

### Vulnerabilities
Analytics computed from your real scans, across four tabs:
- **30-Day Trend** — findings discovered per day
- **By Type** — breakdown by vulnerability type
- **Confidence Score** — distribution by severity band
- **Statistics** — totals and average confidence

Use **Export** for a JSON or CSV snapshot.

### Alerts
Security alerts are raised automatically whenever a scan finds a new vulnerability. Filter by active/resolved, open one for details, and mark it resolved (or reopen it). Export to JSON/CSV.

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

A scan: aggregates subdomains from all configured sources → resolves DNS and groups by IP → probes HTTP(S) (status/title/server, https→http fallback) → fingerprints technologies and flags Cloudflare → optionally port-scans → tests for takeover → stores results, raises alerts, and sends Slack/email notifications when enabled.

> **Port scanning is active.** It's off by default and opt-in per scan — only enable it for targets you're authorized to scan.

## Vulnerability types

| Type | Typical confidence | Meaning |
|------|--------------------|---------|
| S3 bucket takeover | ~95% | CNAME points to an unclaimed S3 bucket |
| CNAME orphan | ~85% | CNAME target doesn't resolve |
| Orphaned NS record | ~85% | NS target doesn't exist |
| Orphaned MX record | ~80% | MX target doesn't exist |

Only findings at or above the confidence threshold (default 75) raise alerts. Findings can be flagged as false positives via the API.
