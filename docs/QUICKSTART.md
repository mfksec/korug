# Quick Start Guide

Get Subdomain Hunter running in minutes with this step-by-step guide.

## 🐳 Docker Setup (Recommended - 5 minutes)

The easiest way to get everything running locally with UI + Backend + Database.

### Prerequisites
- Docker & Docker Compose installed
- Internet connection (first run downloads images)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/mfksec/subdomain_hunter.git
cd subdomain_hunter

# 2. Start all services with one command
docker-compose -f docker/docker-compose.yml up -d

# 3. Wait 10 seconds for services to start
sleep 10

# 4. (Optional) Add your first domain
docker exec subdomain_hunter_app python -m subdomain_hunter.cli add-domain example.com
```

### Access the Application

| Service | URL | Purpose |
|---------|-----|---------|
| **Web Dashboard** | http://localhost:3000 | Main user interface |
| **API Documentation** | http://localhost:8000/docs | Interactive API reference |
| **Database** | localhost:5432 | PostgreSQL (internal) |
| **Redis Cache** | localhost:6379 | Redis (internal) |

### First Login

An admin account is automatically created on first startup. **Find the credentials in the logs:**

```bash
# Check the logs for the auto-generated admin password
docker-compose -f docker/docker-compose.yml logs subdomain-hunter-api | grep -A 5 "admin account"

# Output will show:
# ========================================================================
# No ADMIN_PASSWORD set. Created initial admin account:
#     username: admin
#     password: TrKxL9mN8pQ2vWxYz3jKlMn4oP
# Store this now and change it after first login.
# ========================================================================
```

Use these credentials to log into the dashboard at http://localhost:3000.

⚠️ **IMPORTANT**: 
- Save the password somewhere secure
- Change it immediately after first login (Dashboard → Settings → Account)
- For production deployments, set `ADMIN_PASSWORD` in `docker/.env.docker` to a strong value before starting

### Useful Docker Commands

```bash
# View running containers
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f subdomain-hunter-api

# Stop services
docker-compose -f docker/docker-compose.yml down

# Stop and remove data (fresh start)
docker-compose -f docker/docker-compose.yml down -v

# Restart a service
docker-compose -f docker/docker-compose.yml restart subdomain-hunter-api
```

---

## 💻 Local Development Setup (10 minutes)

For developers who want to modify the code or run without Docker.

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL 12+ (or SQLite for testing)
- Subfinder & Amass (for discovery)

### Backend Setup

```bash
# 1. Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install discovery tools
brew install subfinder amass  # macOS
# or: sudo apt-get install subfinder amass  # Linux

# 4. Copy environment configuration
cp .env.example .env

# 5. Set required environment variables
export DATABASE_URL="sqlite:///./test.db"  # SQLite for local testing
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5174,http://localhost:8000"

# 6. Initialize database
python -m subdomain_hunter.cli init-database

# 7. Create an admin user
python -m subdomain_hunter.cli create-user
# Interactive prompt:
# Username: admin
# Email: admin@localhost
# Password: (secure password, min 8 chars)
# Role: admin

# 8. Start the API server
python -m subdomain_hunter.run
```

Backend will run on `http://localhost:8000`

### Frontend Setup (in a new terminal)

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

Frontend will open automatically at `http://localhost:5174`

### Access the Application

- **Web Dashboard**: http://localhost:5174
- **API Documentation**: http://localhost:8000/docs

---

## 🚀 Your First Workflow

Once everything is running, follow these steps:

### 1. Login to Dashboard
- Go to http://localhost:3000 (Docker) or http://localhost:5174 (Dev)
- Login with `admin` / `admin123`
- **Change your password** (Settings → Account)

### 2. Generate API Key
- Go to Settings (⚙️ icon)
- Click **API Keys**
- Click **Generate New Key**
- Copy and save the key

### 3. Add a Domain
- Go to **Domains** tab
- Click **➕ Add Domain**
- Enter a domain (e.g., `github.com` or `example.com`)
- Click **Add**

### 4. Run a Scan
- Click on the domain you just added
- Click **🔍 Start Scan**
- Wait 2-5 minutes for scan to complete

### 5. View Results
- Go to **Vulnerabilities** tab
- See any detected issues
- Click on a vulnerability for details

### 6. Setup Slack Alerts (Optional)
- Go to Settings → Integrations
- Add your Slack webhook URL
- Future vulnerabilities will send Slack alerts

### 7. Schedule Daily Scans
- Go to Settings → Scanning
- Set scan time and frequency
- Enable scheduled scans
- Scans run automatically every day

---

## 🛠️ Troubleshooting

### Docker Issues

**Error: "Cannot connect to API"**
```bash
# Check if containers are running
docker-compose -f docker/docker-compose.yml ps

# View API logs
docker-compose -f docker/docker-compose.yml logs subdomain-hunter-api
```

**Error: "Database connection failed"**
```bash
# Restart the database
docker-compose -f docker/docker-compose.yml restart postgres

# Wait 10 seconds and try again
sleep 10
docker exec subdomain_hunter_app python -m subdomain_hunter.cli init-database
```

**Port already in use**
```bash
# Kill process using port 3000, 8000, or 5432
# Or modify docker-compose.yml ports: section

# Example change 8000 to 8001:
# "8001:8000"  # 8001 is your new port
```

### Local Development Issues

**Error: "Subfinder/Amass not found"**
```bash
# Verify installation
which subfinder
which amass

# Install if missing
brew install subfinder amass
```

**Error: "PostgreSQL connection refused"**
```bash
# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql

# Or use SQLite instead in .env:
DATABASE_URL=sqlite:///./test.db
```

**Error: "Port 3000 already in use"**
```bash
# Kill the process
lsof -ti:3000 | xargs kill -9

# Or run on different port
cd frontend && npm run dev -- --port 3001
```

---

## 📚 Next Steps

- 📖 [User Guide](USER_GUIDE.md) - Comprehensive dashboard guide
- 🔌 [API Reference](API.md) - REST API endpoints
- 💡 [CLI Reference](CLI.md) - Command-line usage
- 🏗️ [Architecture](ARCHITECTURE.md) - System design
- 🔒 [Security Guide](../SECURITY.md) - Security best practices

---

## 💬 Need Help?

- 🐛 [Report Issues](https://github.com/mfksec/subdomain_hunter/issues)
- 💭 [Discussions](https://github.com/mfksec/subdomain_hunter/discussions)
- 📧 [Contact](mailto:security@example.com)

---

**Happy monitoring! 🛡️**
