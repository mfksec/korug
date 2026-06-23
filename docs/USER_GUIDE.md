# User Guide

A tour of the Körüg web dashboard. Navigation is a left sidebar; the top bar has a light/dark theme toggle and your account menu (Profile, Logout).

## Logging in

Open the dashboard, sign in with your username and password. First-time admin credentials come from the server logs (see [Quick Start](QUICKSTART.md)). Change your password under **Profile**.

## Pages

### Dashboard
At-a-glance stat cards — total domains, vulnerabilities, active scans, high-risk domains — plus the **Monitored Domains** table. Add a domain with **Add Domain**; remove one with the delete icon. Scans are run from the CLI or on the schedule (see below).

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

Scans run automatically on the daily schedule (`SCAN_SCHEDULE_HOUR`/`MINUTE`). To run one now, use the CLI (`korug scan --domain example.com`) or the API (`POST /api/scans/{id}/scan`). A scan discovers subdomains, resolves DNS, scores takeover risk, stores results, raises alerts, and sends Slack/email notifications when enabled.

## Vulnerability types

| Type | Typical confidence | Meaning |
|------|--------------------|---------|
| S3 bucket takeover | ~95% | CNAME points to an unclaimed S3 bucket |
| CNAME orphan | ~85% | CNAME target doesn't resolve |
| Orphaned NS record | ~85% | NS target doesn't exist |
| Orphaned MX record | ~80% | MX target doesn't exist |

Only findings at or above the confidence threshold (default 75) raise alerts. Findings can be flagged as false positives via the API.
