# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Active TLS/SSL configuration audit with tlsx** (opt-in, `ENABLE_TLS_AUDIT`): audits
  the certificate and protocol a host actually serves over the incremental alive host
  set of **active**-mode domains, host-scope-gated exactly like nuclei. Flags expired /
  self-signed / hostname-mismatched / untrusted certs, deprecated protocol versions
  (SSLv3, TLS 1.0/1.1), and weak cipher suites as `tls:<issue>` vulnerabilities
  (higher-confidence problems also raise alerts). Distinct from the passive crt.sh
  certificate monitoring. Fully fault-isolated.
- **masscan → nmap port-scan pipeline** (opt-in, `ENABLE_MASSCAN`): a fast wide-range
  masscan sweep finds open ports, then nmap does service/version detection on just
  those — far faster than a wide nmap scan. Becomes the preferred port-scan engine when
  enabled, falling back to nmap alone or the built-in TCP-connect scan when masscan is
  missing or unprivileged. Honours the same IP-level scope gate (never scans shared CDN
  IPs; respects declared owned ranges).
- **Subdomain brute-force with massdns** (opt-in, `ENABLE_MASSDNS`): resolves
  `<word>.<domain>` candidates from an operator-supplied wordlist against a resolvers
  file at high speed; resolving names join discovery as the `massdns` source. Disabled
  unless both `MASSDNS_WORDLIST` and `MASSDNS_RESOLVERS` are configured.
- **Cloud bucket enumeration** (opt-in, `ENABLE_BUCKET_ENUM`): probes well-known AWS S3,
  GCS, and Azure Blob endpoints for bucket/account names derived from the domain
  keyword. Runs in **active** mode only; a publicly-listable bucket is recorded as a
  `bucket:<provider>:public:<name>` finding and alerted. Native HTTP probes — no external
  binary or credentials. Findings attach to the apex host.

## [0.4.0] - 2026-06-28

### Added
- **Ownership attribution + scope gating for active scanning** ("scope is law"): each
  asset gets an **ownership-confidence** score (name ownership + declared owned IP
  ranges `SCOPE_CIDRS` + hosting classification), shown on the subdomain detail view.
  When `REQUIRE_SCOPE_FOR_ACTIVE` is on (default), intrusive tools are gated:
  - **nuclei** only scans hosts owned by name and **not** hosted on a third-party app
    service (e.g. a CNAME to `github.io`/`herokuapp.com`) — CDN-fronted hosts are fine.
  - **port scan** never targets shared CDN IPs, and (when `SCOPE_CIDRS` is set) only
    scans IPs inside your declared ranges.

## [0.3.0] - 2026-06-28

### Added
- **Active template scanning with nuclei** (opt-in, `ENABLE_NUCLEI`): runs
  ProjectDiscovery's nuclei over the incremental (new/changed alive) host set of
  **active**-mode domains — takeover, CVE, exposure, misconfiguration and
  default-login templates. Findings land as `nuclei:<template-id>` vulnerabilities
  (high/critical also raise alerts). One batch run per scan; fully fault-isolated
  (missing binary / timeout / error never fails a scan). Configurable tags,
  severities and rate limit.
- **Live Certificate Transparency monitoring with certstream** (opt-in,
  `ENABLE_CERTSTREAM`): a self-healing background consumer that watches CT log
  issuances and records brand-new subdomains of monitored domains as discovered
  assets (`sources=certstream`) with a `subdomain_added` change — near real-time
  surface discovery between scheduled scans. Configurable feed URL.

## [0.2.0] - 2026-06-27

### Added
- **Active/passive monitoring mode per domain**: choose how deeply Körüg monitors a
  domain — **active** (discovery + DNS + HTTP probing + tech fingerprint + CVE +
  certificate checks) or **passive** (low-touch: discovery + DNS + DNS-based takeover
  only, no direct probing of the target). Selectable when adding a domain and editable
  from the domain detail view (`Domain.monitor_mode`; default `active`). Port scans
  remain manual in both modes.
- **Precise subdomain-takeover detection** (`can-i-take-over-xyz` style): a new
  `subdomain_takeover` finding fires when a CNAME points at a known service
  (GitHub Pages, Heroku, Shopify, Fastly, Ghost, Bitbucket, and ~25 more) **and**
  the target is dangling (NXDOMAIN) or the HTTP body matches the service's
  "unclaimed" fingerprint. Far fewer false positives than the generic CNAME-orphan
  check, which now only fires when no specific service matched
  (`services/takeover_fingerprints.py`).
- **Subdomain detail view**: every discovered subdomain is now clickable, opening
  a per-host page with DNS records, fingerprint, open ports, vulnerabilities,
  certificates, and a change timeline (`GET /api/scans/subdomain/{id}`).
- **Certificate Transparency monitoring**: certificates are fetched from crt.sh,
  stored per host, shown in the detail view, and a newly-observed certificate
  raises a change/alert (`services/certificates.py`, `Certificate` model).
- **Attack-surface change tracking**: scans diff each host against its prior state
  and record an `AssetChange` log (subdomain added/removed/reappeared, went
  live/offline, IP/tech/port changes, new certificate), surfaced on a new
  **Changes** page and `GET /api/changes/`. Significant changes raise alerts.
- **Automatic incremental CVE scanning**: after discovery, new/changed alive hosts
  are checked against NVD automatically (previously manual-only), gated by
  `ENABLE_AUTO_CVE` and bounded to keep scans fast.
- **Gone-asset tracking**: subdomains that disappear from discovery are flagged
  `is_gone` (kept for history) instead of being dropped.
- **Sort + filter everywhere**: added to the Domain detail, Alerts, and Audit log
  views; the new Assets and Changes views are fully sortable/filterable too.
- **Assets page**: a dedicated, searchable/filterable view of every discovered
  subdomain across all domains (`GET /api/scans/assets`), now clickable into the
  subdomain detail view, with gone-state filtering and server-side sort.
- **Live scan status**: domain rows show a live "Scanning…" state, backed by
  `GET /api/scans/active` and `GET /api/scans/{id}/scan/status`.
- **Stop scan**: cooperative cancellation via `POST /api/scans/{id}/scan/cancel`;
  both discovery and enrichment observe the request and stop promptly.
- Startup reconciliation marks scans orphaned by a restart as `failed` instead
  of leaving them stuck in `running`/`cancelling`.
- `ENABLE_SUBFINDER` / `ENABLE_AMASS` settings to control local CLI discovery.
- Docker dev override (`docker/docker-compose.override.yml`) for API live-reload.

### Changed
- The daily scheduler is now a continuous-monitoring loop: each run diffs the
  surface and records changes, not just a fresh snapshot.
- New settings `ENABLE_AUTO_CVE` and `ENABLE_CERT_MONITORING` gate the network-bound
  incremental scan steps (both default on; disabled in the test suite).
- Scans now persist **all** discovered subdomains (flagging resolve/alive state)
  instead of dropping names that don't currently resolve.
- Discovery runs the local CLI tools concurrently with the passive HTTP sources
  rather than serially, and amass is now opt-in — large reduction in scan time.

## [0.1.0] - 2026-06-18

### Added
- Initial release of Körüg
- Multi-source subdomain discovery (Subfinder, Amass, Shodan.io, urlscan.io)
- Subdomain takeover vulnerability detection with confidence scoring
- REST API with 8+ endpoints
- CLI tool with 7 major commands
- PostgreSQL database with proper schema
- Slack integration for notifications
- XLSX export functionality
- Docker and docker-compose setup
- Comprehensive test suite
- Full documentation and guides
- GitHub Actions workflows for testing

### Features
- ✅ Domain management (add, remove, list, update)
- ✅ Automated scanning with background tasks
- ✅ Vulnerability tracking and false positive marking
- ✅ Historical scan data and trending
- ✅ API key authentication
- ✅ Environment-based configuration
- ✅ Multiple discovery sources with fallback
- ✅ S3 bucket takeover detection
- ✅ CNAME orphan detection
- ✅ DNS record orphan detection
- ✅ Confidence-based alerting (75% threshold)

### Fixed
- N/A (initial release)

### Known Issues
- No web dashboard yet (planned for v0.2.0)
- Single scheduler instance (multi-instance scaling in v0.2.0)
- No webhook support beyond Slack (planned for v0.2.0)

## Roadmap

### Planned for v0.2.0
- Web dashboard (React/Vue)
- Email notifications
- Webhook integrations
- Advanced analytics and reporting
- Performance optimizations (parallel scanning)
- Multi-tenant support
- Enhanced authentication (OAuth/JWT)

### Planned for v0.3.0
- Kubernetes integration
- Metrics and monitoring (Prometheus)
- Advanced filtering and reporting
- Custom discovery rules
- Bulk domain import/export
