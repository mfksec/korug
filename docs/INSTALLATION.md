# Installation

## Docker (recommended)

```bash
git clone https://github.com/mfksec/korug.git
cd korug
cp docker/.env.docker docker/.env     # Docker config; set secrets + DB credentials
docker compose -f docker/docker-compose.yml up -d --build
curl http://localhost:8000/health
```

Dashboard: http://localhost:3000 · API docs: http://localhost:8000/docs

> Configure Docker via `docker/.env` (Compose loads its env file from the compose
> file's directory). Use the `docker/.env.docker` template — its `DATABASE_URL`
> points at the `postgres` service. The root `.env.example` is for non-Docker
> local runs and targets `localhost`. See [Quick Start → Configuration &
> credentials](QUICKSTART.md#configuration--credentials) for required secrets,
> PostgreSQL credentials, and the full command set.

## Local development

Requirements: Python 3.11+, Node.js 20.19+ or 22.12+ (required by Vite 8), PostgreSQL 14+ (or SQLite for testing), and Subfinder/Amass for discovery.

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
| `SHODAN_API_KEY` / `URLSCAN_API_KEY` / `VIRUSTOTAL_API_KEY` / `SECURITYTRAILS_API_KEY` / `BINARYEDGE_API_KEY` | no | key-gated discovery sources (free sources need no key) |
| `CENSYS_API_ID` / `CENSYS_API_SECRET` | no | Censys Search v2 source (both required) |
| `SUBFINDER_PATH` / `AMASS_PATH` | no | tool locations |
| `ENABLE_SUBFINDER` / `ENABLE_AMASS` | no | local CLI discovery tools; subfinder on by default, amass opt-in (off — slow, little value unconfigured) |
| `ENABLE_HTTP_PROBE` | no | HTTP(S) probe of live subdomains (default true) |
| `ENABLE_PORT_SCAN` / `PORT_SCAN_PORTS` | no | default port scan on/off + port list (also toggled per scan in the UI) |
| `NMAP_PATH` / `NMAP_SERVICE_DETECTION` | no | nmap location + `-sV` service detection (falls back to a built-in TCP scan) |
| `ENRICHMENT_CONCURRENCY` / `HTTP_PROBE_TIMEOUT` | no | enrichment tuning |
| `SCAN_SCHEDULE_HOUR` / `SCAN_SCHEDULE_MINUTE` | no | daily scan time (UTC) |
| `CONFIDENCE_THRESHOLD` | no | minimum score to alert (default 75) |

> Slack and email are configured at runtime from the **Integrations** page (stored in the database), not via env vars. Most discovery sources are free and need no key; the keys above only unlock extra providers. Port scanning is active — keep it off unless you're authorized to scan the targets. The Docker image ships with nmap; for local installs, `brew install nmap` (or `apt-get install nmap`) to get service/version detection.

## Troubleshooting

- **Port in use** — set `PORT=8001` (API) or run the frontend with `npm run dev -- --port 3001`.
- **PostgreSQL refused** — verify `DATABASE_URL`, or use SQLite for local work.
- **Subfinder/Amass not found** — install them and/or set `SUBFINDER_PATH` / `AMASS_PATH`.
- **Tests** — `pip install -r requirements.txt && pytest tests/ -v`.
