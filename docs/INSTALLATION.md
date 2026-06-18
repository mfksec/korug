# Installation & Setup Guide

## Quick Start

### Using Docker (Recommended)

```bash
git clone https://github.com/mfksec/subdomain_hunter.git
cd subdomain_hunter

# Copy environment template
cp .env.example .env

# Start services
docker-compose -f docker/docker-compose.yml up -d

# Initialize database
docker exec subdomain_hunter_app python -m subdomain_hunter.cli init-database

# Test it's running
curl http://localhost:8000/health
```

Visit: `http://localhost:8000/docs` to see the API documentation.

### Local Development Setup

#### Requirements
- Python 3.11+
- PostgreSQL 14+
- Subfinder
- Amass

#### Installation Steps

```bash
# Clone repository
git clone https://github.com/mfksec/subdomain_hunter.git
cd subdomain_hunter

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install external tools (macOS)
brew install subfinder amass

# Setup environment
cp .env.example .env
# Edit .env with your settings
```

#### Database Setup

```bash
# Ensure PostgreSQL is running
psql -U postgres

# Create database and user
CREATE DATABASE subdomain_hunter;
CREATE USER subdomain_user WITH PASSWORD 'subdomain_password';
GRANT ALL PRIVILEGES ON DATABASE subdomain_hunter TO subdomain_user;
\q

# Initialize schema
python -m subdomain_hunter.cli init-database
```

#### Run Application

```bash
# Terminal 1: FastAPI server
python -m subdomain_hunter.run

# Terminal 2: Use CLI or visit http://localhost:8000/docs
python -m subdomain_hunter.cli list-domains
```

## Configuration

### Environment Variables

Create `.env` file with your settings:

```bash
# Database
DATABASE_URL=postgresql://subdomain_user:password@localhost:5432/subdomain_hunter

# API
FASTAPI_ENV=development
FASTAPI_DEBUG=true
API_KEY=your-secret-api-key

# Tools
SUBFINDER_PATH=/usr/local/bin/subfinder
AMASS_PATH=/usr/local/bin/amass

# External APIs (Optional)
SHODAN_API_KEY=your-shodan-key
URLSCAN_API_KEY=your-urlscan-key

# Slack (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_ENABLED=false

# Scanning
SCAN_SCHEDULE_HOUR=0
SCAN_SCHEDULE_MINUTE=0
CONFIDENCE_THRESHOLD=75
```

### Getting API Keys

#### Shodan.io
1. Visit https://www.shodan.io/
2. Sign up and navigate to Account Settings
3. Copy API key to `.env`

#### urlscan.io
1. Visit https://urlscan.io/
2. Create account
3. Get API key from Settings

#### Slack Webhook
1. Create Slack app at https://api.slack.com/apps
2. Enable Incoming Webhooks
3. Add webhook URL to `.env`

## Troubleshooting

### Port 8000 Already in Use
```bash
# Use different port
export PORT=8001
python -m subdomain_hunter.run
```

### PostgreSQL Connection Error
```bash
# Check PostgreSQL is running
psql -U subdomain_user -d subdomain_hunter -c "SELECT 1"

# Check connection string in .env
DATABASE_URL=postgresql://subdomain_user:password@localhost:5432/subdomain_hunter
```

### Subfinder/Amass Not Found
```bash
# macOS
brew install subfinder amass

# Ubuntu/Debian
sudo apt-get install subfinder

# Or download from GitHub
# https://github.com/projectdiscovery/subfinder
# https://github.com/OWASP/Amass
```

### Tests Failing
```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Run tests with verbose output
pytest tests/ -v --tb=short
```

## Next Steps

- Read [API Documentation](./api.md)
- Check [CLI Usage](./cli.md)
- Review [Architecture](./architecture.md)
- See [Contributing Guide](../CONTRIBUTING.md)
