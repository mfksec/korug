# Subdomain Hunter

A comprehensive subdomain security monitoring tool that discovers subdomains across multiple sources, detects takeover vulnerabilities, and integrates with Slack for real-time notifications and continuous monitoring.

> **⚡ TL;DR**: Want to get started NOW? → [**Quick Start Guide**](docs/QUICKSTART.md) (5 minutes with Docker!)

## 🎯 Overview

Subdomain Hunter automates subdomain discovery and vulnerability detection for organizations that want to monitor their entire domain ecosystem. It combines multiple discovery sources (Subfinder, Amass, Shodan, urlscan) with intelligent takeover detection to identify security gaps before attackers do.

### Perfect For:
- **Security Teams**: Monitor and track subdomain security posture
- **DevOps/Infrastructure**: Discover forgotten or legacy subdomains  
- **Penetration Testers**: Comprehensive domain reconnaissance
- **Bug Bounty Hunters**: Automated subdomain enumeration at scale

## ✨ Features

- 🔍 **Multi-Source Discovery**
  - Subfinder (fast passive enumeration)
  - Amass (comprehensive active/passive scanning)
  - Shodan API (IP/port intelligence)
  - urlscan.io API (URL archive data)
  - DNS resolution (A/AAAA/CNAME/MX/NS records)

- 🛡️ **Vulnerability Detection**
  - S3 bucket takeover detection (95% confidence)
  - CNAME orphan identification (85% confidence)
  - DNS orphan discovery (80-85% confidence)
  - Confidence-based scoring system

- 🚀 **Integration & Automation**
  - REST API with interactive documentation (FastAPI/Swagger)
  - CLI tool for scripting and automation
  - Slack real-time notifications
  - Scheduled recurring scans
  - Bulk domain management

- 📊 **Reporting & Analysis**
  - Historical scan tracking and trend analysis
  - XLSX export with formatted reports
  - False positive feedback and flagging
  - Domain management with metadata

- 🐳 **Deployment Ready**
  - Docker containerization with docker-compose
  - PostgreSQL backend with SQLAlchemy ORM
  - Environment-based configuration
  - Graceful API fallback for optional services

## 🚀 Quick Start

**Docker Setup (5 minutes):**
```bash
git clone https://github.com/mfksec/subdomain_hunter.git
cd subdomain_hunter
docker-compose -f docker/docker-compose.yml up -d
sleep 10
```

**Access:**
- 🌐 **Web Dashboard**: http://localhost:3000
- 📚 **API Docs**: http://localhost:8000/docs

**First Login:**
Check the application logs for the auto-generated admin password:
```bash
docker-compose -f docker/docker-compose.yml logs subdomain-hunter-api | grep -A 5 "admin account"
```

For **local development** or **detailed setup**, see [Quick Start Guide](docs/QUICKSTART.md).

---

## 📱 Web Dashboard

**Main Tabs:**
- **Dashboard**: Overview, trends, recent alerts
- **Domains**: Add/manage domains, view subdomains and DNS records
- **Vulnerabilities**: View detected issues, mark false positives
- **Alerts**: Slack notifications history
- **Audit Logs**: Security event tracking
- **Settings**: API keys, Slack integration, scanning config

See [User Guide](docs/USER_GUIDE.md) for detailed feature walkthrough.

---

## 📖 Documentation

- [**Quick Start**](docs/QUICKSTART.md) - 5-minute setup & troubleshooting
- [**Authentication**](docs/AUTH.md) - User management, JWT tokens, security
- [**User Guide**](docs/USER_GUIDE.md) - Dashboard features & workflows
- [**API Reference**](docs/API.md) - REST endpoints & authentication
- [**CLI Reference**](docs/CLI.md) - Command-line tool & user management
- [**Architecture**](docs/ARCHITECTURE.md) - System design
- [**Installation**](docs/INSTALLATION.md) - Detailed setup
- [**Security**](SECURITY.md) - Vulnerability reporting
- [**Contributing**](CONTRIBUTING.md) - Development guidelines

## ⚙️ Configuration

Create `.env` from `.env.example` and set required variables:

**REQUIRED** (for both local & Docker):
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - API secret (min 32 bytes)
- `API_KEY` - API key for service-to-service auth
- `ALLOWED_ORIGINS` - CORS origins (e.g., `http://localhost:3000`)

**OPTIONAL**:
- `REDIS_URL` - Redis URL (for distributed rate limiting)
- `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` - Admin seeding
- `SLACK_WEBHOOK_URL`, `SHODAN_API_KEY`, `URLSCAN_API_KEY` - Integrations
- See [Authentication](docs/AUTH.md) for full auth configuration

## 🏗️ Architecture

**Tech Stack:**
- **Backend**: FastAPI, PostgreSQL, SQLAlchemy
- **Frontend**: React, TypeScript, Material-UI
- **Discovery**: Subfinder, Amass, Shodan, urlscan APIs
- **Security**: JWT authentication, Bcrypt hashing, audit logging

See [Architecture Docs](docs/ARCHITECTURE.md) for detailed design.

## 🔐 Security

Subdomain Hunter includes enterprise-grade security features:

- **Authentication**: JWT-based API authentication with type validation
- **Password Security**: Bcrypt hashing for all credentials
- **CORS Protection**: Explicit origin whitelist
- **Rate Limiting**: Built-in protection against brute force attacks
- **Audit Logging**: Comprehensive JSON audit trail for compliance
- **Security Headers**: XSS, clickjacking, and MIME sniffing protection
- **Environment Secrets**: No hardcoded credentials anywhere
- **Token Revocation**: Logout invalidates tokens immediately

See [SECURITY.md](SECURITY.md) for detailed security guidelines, production deployment checklist, and vulnerability reporting.

## 📋 Requirements

- **Python**: 3.11+ | **Database**: PostgreSQL 12+ | **Docker**: For containerized deployment
- **Memory**: 512MB minimum, 2GB recommended

## 🛠️ Development

```bash
# Setup
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start API server
python -m subdomain_hunter.run
```

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🔐 Security

**For security vulnerabilities**: See [SECURITY.md](SECURITY.md). Do NOT create public GitHub issues for security bugs.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 💬 Support & Resources

- 📚 [Full Documentation](docs/)
- 🐛 [Report Issues](https://github.com/mfksec/subdomain_hunter/issues)
- 📧 [Security Contact](security@amboss.com)