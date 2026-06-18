# Subdomain Hunter

A comprehensive subdomain security monitoring tool that discovers subdomains, detects takeover vulnerabilities, and integrates with Slack for continuous monitoring.

## Features

- 🔍 **Multi-Source Discovery**: Subfinder, Amass, Shodan.io, urlscan.io
- 🛡️ **Takeover Detection**: S3 buckets, CNAME orphans, DNS records with confidence scoring
- 📊 **REST API**: Full-featured API with FastAPI automatic documentation
- 💻 **CLI Tool**: Command-line interface for automation
- 📈 **Tracking**: Historical data and trend analysis
- 🔔 **Slack Integration**: Real-time notifications and summaries
- 📋 **XLSX Export**: Formatted reports for sharing
- 🐳 **Docker Ready**: Complete containerization with docker-compose

## Quick Start

### Using Docker (1 minute setup)

```bash
git clone https://github.com/mfksec/subdomain_hunter.git
cd subdomain_hunter
cp .env.example .env
docker-compose -f docker/docker-compose.yml up -d
docker exec subdomain_hunter_app python -m subdomain_hunter.cli init-database
docker exec subdomain_hunter_app python -m subdomain_hunter.cli add-domain example.com
```

Visit: **http://localhost:8000/docs** to see the interactive API documentation.

### Local Development

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install subfinder amass
cp .env.example .env
python -m subdomain_hunter.cli init-database
python -m subdomain_hunter.run
```

## Documentation

- 📖 [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- 🔌 [API Reference](docs/API.md) - REST API endpoints and examples
- 💡 [CLI Reference](docs/CLI.md) - Command-line tool usage
- 🏗️ [Architecture](docs/ARCHITECTURE.md) - System design and components
- 📝 [Contributing](CONTRIBUTING.md) - How to contribute
- ⚖️ [Security Policy](SECURITY.md) - Reporting vulnerabilities

## Common Commands

```bash
# Add and manage domains
subdomain-hunter add-domain example.com
subdomain-hunter list-domains
subdomain-hunter remove-domain example.com

# Run scans
subdomain-hunter scan --domain example.com
subdomain-hunter show-results example.com

# Export data
subdomain-hunter export example.com --format xlsx

# API requests
curl http://localhost:8000/api/domains/ -H "Authorization: Bearer YOUR_API_KEY"
curl -X POST http://localhost:8000/api/scans/1/scan -H "Authorization: Bearer YOUR_API_KEY"
```

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/subdomain_hunter

# Optional APIs (with graceful fallback if not provided)
SHODAN_API_KEY=your-shodan-key
URLSCAN_API_KEY=your-urlscan-key

# Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_ENABLED=true

# Scanning
CONFIDENCE_THRESHOLD=75  # Only alert on findings >= 75% confidence
SCAN_SCHEDULE_HOUR=0     # Daily scan at 00:00 UTC
```

## Key Capabilities

### Subdomain Discovery
- ✅ Subfinder (fast passive enumeration)
- ✅ Amass (comprehensive discovery)  
- ✅ Shodan.io API (IP/port data)
- ✅ urlscan.io API (URL archive)
- ✅ DNS resolution with A/AAAA/CNAME/MX/NS records

### Vulnerability Detection
| Type | Confidence | Detection |
|------|-----------|-----------|
| S3 Bucket Takeover | 95% | CNAME to unclaimed S3 bucket |
| CNAME Orphan | 85% | CNAME target doesn't exist |
| DNS Orphans | 80-85% | MX/NS without valid targets |

### Management
- ✅ False positive feedback
- ✅ Historical scan tracking
- ✅ Bulk domain management
- ✅ XLSX export with formatting
- ✅ Real-time Slack alerts

## Project Status

| Phase | Status | Details |
|-------|--------|---------|
| Core Backend | ✅ Complete | FastAPI, PostgreSQL, ORM models |
| Discovery | ✅ Complete | Multi-source with fallback |
| Detection | ✅ Complete | 3 vulnerability types with scoring |
| API | ✅ Complete | 8+ REST endpoints |
| CLI | ✅ Complete | 7 major commands |
| Docker | ✅ Complete | Full containerization |
| Tests | ✅ Complete | 20+ test cases |
| Dashboard | 🔄 Planned | React/Vue web UI (v0.2) |
| Email Alerts | 🔄 Planned | Email notifications (v0.2) |
| Webhooks | 🔄 Planned | Custom integrations (v0.2) |

## License

MIT License - See [LICENSE](LICENSE) file

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

For security issues, please see [SECURITY.md](SECURITY.md) - do not open public issues.

## Support

- 📚 Check [documentation](docs/)
- 🐛 [Report issues](https://github.com/mfksec/subdomain_hunter/issues)
- 💬 [Start a discussion](https://github.com/mfksec/subdomain_hunter/discussions)
