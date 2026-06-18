# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-18

### Added
- Initial release of Subdomain Hunter
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

## [Unreleased]

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
