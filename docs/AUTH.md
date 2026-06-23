# Authentication & Users

## Authentication

**JWT (dashboard & users).** Log in with username/password to receive an **access token** (1 hour) and a **refresh token** (7 days). Send the access token as `Authorization: Bearer <token>`; refresh it at `POST /api/auth/refresh`. Logout revokes the token (Redis-backed when `REDIS_URL` is set, in-memory otherwise).

**API key (services).** For scripts and integrations, send the `API_KEY` env value as a bearer token. Keep it in the environment, never in code.

Passwords are stored with bcrypt and verified in constant time.

## Roles

| Role | Can do |
|------|--------|
| `admin` | Everything: manage domains, users, integrations; view all audit logs |
| `viewer` | Read-only: domains, vulnerabilities, alerts, results |

Admin-only API endpoints return `403` for viewers. The dashboard hides admin-only pages (Users; editing Integrations) from viewers.

## Managing users

Three ways, same effect:

- **Dashboard** → **Users** (admin): create, change role, enable/disable, reset password, delete. Any user can change their own email/password under **Profile**.
- **API**: `/api/users/*` — admin CRUD plus self-service `/api/users/me` and `/api/users/me/password` (see [API Reference](API.md)).
- **CLI**: `create-user`, `list-users`, `delete-user`, `change-password` (see [CLI Reference](CLI.md)).

Guards prevent deleting/demoting/deactivating yourself or the last remaining admin.

## First-run admin

On first start (no users yet) an admin account is seeded from `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD`. If `ADMIN_PASSWORD` is blank, a strong random password is generated and printed to the logs once:

```
No ADMIN_PASSWORD set. Created initial admin account:
    username: admin
    password: <shown once — save it>
```

Log in and change it under **Profile**.

## Production checklist

- Strong, random `JWT_SECRET_KEY` (32+ bytes) and `API_KEY`.
- Set a real `ADMIN_PASSWORD` before first start.
- Restrict `ALLOWED_ORIGINS` to your domains; serve over HTTPS.
- Set `REDIS_URL` so token revocation and rate limiting work across workers.
- Rotate API keys and review **Audit Logs** periodically.
