# Installation

## Docker (recommended)

```bash
git clone https://github.com/mfksec/korug.git
cd korug
cp .env.example .env     # fill in the required values below
docker compose -f docker/docker-compose.yml up -d
curl http://localhost:8000/health
```

Dashboard: http://localhost:3000 · API docs: http://localhost:8000/docs

## Local development

Requirements: Python 3.11+, Node.js 18+, PostgreSQL 14+ (or SQLite for testing), and Subfinder/Amass for discovery.

**Backend**

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
brew install subfinder amass            # macOS

export DATABASE_URL="sqlite:///./korug.db"   # or a postgresql:// URL
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ALLOWED_ORIGINS="http://localhost:5173,http://localhost:8000"

python -m korug.cli init-database
python -m korug.cli create-user        # interactive: username, email, password, role
python -m korug.run                    # API on :8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                            # dashboard on :5173
```

## Environment variables

Set in `.env` (or the shell / `docker/.env.docker`). See [.env.example](../.env.example) for the full list.

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | yes | `postgresql://…` or `sqlite:///./korug.db` |
| `JWT_SECRET_KEY` | yes | 32+ random bytes |
| `API_KEY` | yes | service-to-service key |
| `ALLOWED_ORIGINS` | yes | comma-separated CORS origins |
| `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | no | first-run admin seed; blank password → auto-generated and logged |
| `REDIS_URL` | no | distributed rate limiting & token revocation |
| `SHODAN_API_KEY` / `URLSCAN_API_KEY` | no | extra discovery sources |
| `SUBFINDER_PATH` / `AMASS_PATH` | no | tool locations |
| `SCAN_SCHEDULE_HOUR` / `SCAN_SCHEDULE_MINUTE` | no | daily scan time (UTC) |
| `CONFIDENCE_THRESHOLD` | no | minimum score to alert (default 75) |

> Slack and email are configured at runtime from the **Integrations** page (stored in the database), not via env vars.

## Troubleshooting

- **Port in use** — set `PORT=8001` (API) or run the frontend with `npm run dev -- --port 3001`.
- **PostgreSQL refused** — verify `DATABASE_URL`, or use SQLite for local work.
- **Subfinder/Amass not found** — install them and/or set `SUBFINDER_PATH` / `AMASS_PATH`.
- **Tests** — `pip install -r requirements.txt && pytest tests/ -v`.
