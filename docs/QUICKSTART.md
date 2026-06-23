# Quick Start

Get Körüg running with Docker in a few minutes.

## 1. Start the stack

```bash
git clone https://github.com/mfksec/korug.git
cd korug
cp .env.example .env     # set DATABASE_URL, JWT_SECRET_KEY, API_KEY, ALLOWED_ORIGINS
docker compose -f docker/docker-compose.yml up -d
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |

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

Findings then appear under **Vulnerabilities** and **Alerts**. Scans also run automatically on the daily schedule.

## 4. (Optional) Notifications

Go to **Integrations** (admin) to add a Slack webhook or SMTP email settings and send a test message.

## Useful commands

```bash
docker compose -f docker/docker-compose.yml ps            # status
docker compose -f docker/docker-compose.yml logs -f korug-api
docker compose -f docker/docker-compose.yml down          # stop
docker compose -f docker/docker-compose.yml down -v       # stop + wipe data
```

For local (non-Docker) development, see [Installation](INSTALLATION.md).
