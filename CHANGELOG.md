# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Assets page**: a dedicated, searchable/filterable view of every discovered
  subdomain across all domains (`GET /api/scans/assets`).
- **Live scan status**: domain rows show a live "Scanning…" state, backed by
  `GET /api/scans/active` and `GET /api/scans/{id}/scan/status`.
- **Stop scan**: cooperative cancellation via `POST /api/scans/{id}/scan/cancel`;
  both discovery and enrichment observe the request and stop promptly.
- Startup reconciliation marks scans orphaned by a restart as `failed` instead
  of leaving them stuck in `running`/`cancelling`.
- `ENABLE_SUBFINDER` / `ENABLE_AMASS` settings to control local CLI discovery.
- Docker dev override (`docker/docker-compose.override.yml`) for API live-reload.

### Changed
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
