# Quick Start

Get Körüg running with Docker in a few minutes.

## 1. Start the stack

```bash
git clone https://github.com/mfksec/korug.git
cd korug
cp docker/.env.docker docker/.env     # Docker-ready config; edit secrets (see below)
docker compose -f docker/docker-compose.yml up -d --build
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |

> **Use `docker/.env.docker`, not the root `.env.example`.** Compose loads its
> env file from the compose file's directory (`docker/.env`), and the Docker
> template points the database at the `postgres` **service** host. The root
> `.env.example` is for non-Docker local runs and points at `localhost`, which
> won't resolve from inside the API container.

## Configuration & credentials

All Docker settings live in `docker/.env` (copied from `docker/.env.docker`).
Compose substitutes them into the stack via `${VAR}` references.

**Required — set strong secrets before any real deployment:**

```bash
# Generate and drop these into docker/.env
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"
```

**PostgreSQL credentials.** The database user/password/name are set on the
`postgres` container, and the API reaches it via `DATABASE_URL` — **the two must
match**, and the host must be `postgres` (the compose service name), not
`localhost`. The `docker/.env.docker` defaults are user `postgres` / db `korug`:

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<a-strong-password>
POSTGRES_DB=korug
# Must match the three values above; host is the service name "postgres":
DATABASE_URL=postgresql://postgres:<a-strong-password>@postgres:5432/korug
```

```bash
# Generate a strong DB password
openssl rand -base64 24

# First, confirm the user/db the running containers actually use
docker compose -f docker/docker-compose.yml exec postgres env | grep POSTGRES
docker compose -f docker/docker-compose.yml exec korug-api printenv DATABASE_URL

# Open a psql shell (use the POSTGRES_USER from above — `postgres` by default)
docker compose -f docker/docker-compose.yml exec postgres psql -U postgres -d korug
```

> **Gotcha — credentials are baked in on first run.** `POSTGRES_USER`,
> `POSTGRES_PASSWORD`, and `POSTGRES_DB` are only applied when the data volume is
> **first** created (empty). Changing them in `docker/.env` later has **no
> effect** on an existing database — the original role/password/db persist.
> (A `psql -U korug` against a stock install fails with `role "korug" does not
> exist` for exactly this reason — the default user is `postgres`.)
>
> To set a custom username, do it **before the first `up`** (or wipe the volume).
> To change the **password** on an existing database, rotate it in-place:
>
> ```bash
> docker compose -f docker/docker-compose.yml exec postgres \
>   psql -U postgres -d korug -c "ALTER USER postgres WITH PASSWORD 'new-password';"
> # then set the same password in POSTGRES_PASSWORD + DATABASE_URL and: up -d
> ```
>
> Or wipe and re-init from scratch (**destroys all data**), which re-reads all
> `POSTGRES_*` values:
> `docker compose -f docker/docker-compose.yml down -v && docker compose -f docker/docker-compose.yml up -d`

**Optional settings** (`docker/.env`):

| Variable | Purpose |
|----------|---------|
| `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | first-run admin seed; blank password → auto-generated and logged |
| `ALLOWED_ORIGINS` | CORS origins for the dashboard (must include the URL you load the UI from) |
| `VITE_API_BASE_URL` | API URL the browser calls; change from `http://localhost:8000` if deploying on a remote host (rebuild the UI after changing) |
| `ENABLE_AMASS` / `ENABLE_SUBFINDER` | local CLI discovery tools (amass opt-in; off by default) |
| `ENABLE_PORT_SCAN` / `PORT_SCAN_PORTS` | active port scan default + ports |
| `SHODAN_API_KEY` / `URLSCAN_API_KEY` / `VIRUSTOTAL_API_KEY` / `CENSYS_API_ID` + `CENSYS_API_SECRET` | optional key-gated discovery sources |

## 2. Get the admin password

On first run an `admin` account is created. If `ADMIN_PASSWORD` is unset, a random password is printed once in the logs:

```bash
docker compose -f docker/docker-compose.yml logs korug-api | grep -A2 "admin account"
```

Log in at http://localhost:3000 and change it under **Profile** (avatar menu → Profile). For production, set a strong `ADMIN_PASSWORD` before the first start.

## 3. Add a domain and scan it

Add domains in the dashboard (**Dashboard → Add Domain**), or from the CLI:

```bash
docker exec korug_app python -m korug.cli add-domain example.com
docker exec korug_app python -m korug.cli scan --domain example.com
```

A running scan shows a live **Scanning…** status with a **Stop** button on its row. Discovered subdomains appear on the **Assets** page (searchable, across all domains); takeover findings appear under **Vulnerabilities** and **Alerts**. Scans also run automatically on the daily schedule.

## 4. (Optional) Notifications

Go to **Integrations** (admin) to add a Slack webhook or SMTP email settings and send a test message.

## Useful commands

```bash
docker compose -f docker/docker-compose.yml ps            # status
docker compose -f docker/docker-compose.yml logs -f korug-api
docker compose -f docker/docker-compose.yml up -d --build  # rebuild after pulling updates
docker compose -f docker/docker-compose.yml down          # stop
docker compose -f docker/docker-compose.yml down -v       # stop + wipe data
```

**Still seeing the old version after an update?** Docker reused cached images. Rebuild from scratch:

```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d --force-recreate
```

Then hard-refresh the browser (Cmd/Ctrl+Shift+R).

For local (non-Docker) development, see [Installation](INSTALLATION.md).
