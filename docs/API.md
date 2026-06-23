# API Reference

Base URL: `http://localhost:8000`. Interactive docs: **`/docs`** (Swagger) and `/redoc`.

## Authentication

Two ways to authenticate; both use a bearer token.

**JWT (users)** — log in, then send the access token on each request:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"…"}'
# → { "access_token": "…", "refresh_token": "…" }

curl http://localhost:8000/api/domains/ -H "Authorization: Bearer <access_token>"
```

Access tokens last 1 hour; exchange a refresh token at `POST /api/auth/refresh`. Logout revokes the token.

**API key (services)** — send the `API_KEY` value as a bearer token: `Authorization: Bearer <API_KEY>`.

See [Authentication & Users](AUTH.md) for roles and details.

## Endpoints

Admin-only endpoints are marked 🔒.

### Auth
| Method | Path |
|--------|------|
| POST | `/api/auth/login` |
| POST | `/api/auth/refresh` |
| POST | `/api/auth/logout` |
| GET | `/api/auth/me` |

### Domains
| Method | Path | |
|--------|------|--|
| GET / POST | `/api/domains/` | list / create |
| GET / PUT / DELETE | `/api/domains/{id}` | get / update / delete |
| GET | `/api/domains/stats/dashboard` | dashboard totals |

### Scans
| Method | Path | |
|--------|------|--|
| POST | `/api/scans/{domain_id}/scan` | trigger scan (`?port_scan=true` to include a port scan) |
| GET | `/api/scans/{domain_id}/results` | enriched results: subdomains, IP groups, vulnerabilities |
| GET | `/api/scans/history/{domain_id}` | scan history |

### Vulnerabilities
| Method | Path | |
|--------|------|--|
| GET | `/api/vulnerabilities/` | list (filter by `domain_id`, `vuln_type`) |
| GET / PATCH / DELETE | `/api/vulnerabilities/{id}` | get / flag false positive / delete |
| GET | `/api/vulnerabilities/stats/summary` | totals by severity & type |
| GET | `/api/vulnerabilities/stats/timeline?days=30` | daily trend |
| GET | `/api/vulnerabilities/stats/confidence-distribution` | severity bands |

### Alerts
| Method | Path | |
|--------|------|--|
| GET | `/api/alerts/` | list (filter by `status`, `severity`, `domain`) |
| GET | `/api/alerts/{id}` | get |
| POST | `/api/alerts/{id}/resolve` · `/unresolve` | change status |
| DELETE | `/api/alerts/{id}` | delete |
| GET | `/api/alerts/stats/summary` | counts by status & severity |

### Users
| Method | Path | |
|--------|------|--|
| GET / POST | `/api/users/` 🔒 | list / create |
| GET / PATCH / DELETE | `/api/users/{id}` 🔒 | get / update role·email·active / delete |
| POST | `/api/users/{id}/password` 🔒 | reset a user's password |
| GET / PATCH | `/api/users/me` | own profile |
| POST | `/api/users/me/password` | change own password |

### Integrations
| Method | Path | |
|--------|------|--|
| GET | `/api/integrations/` | current config (secrets masked) |
| PUT | `/api/integrations/slack` 🔒 · `/email` 🔒 | update |
| POST | `/api/integrations/slack/test` 🔒 · `/email/test` 🔒 | send a test |

### Settings
| Method | Path | |
|--------|------|--|
| GET / POST | `/api/settings/settings/user` | preferences |
| GET / POST | `/api/settings/apikeys` | list / create API key |
| POST / DELETE | `/api/settings/apikeys/{id}/revoke` · `/api/settings/apikeys/{id}` | revoke / delete |
| GET | `/api/settings/audit-logs` | audit entries (own; admins see all) |
| GET | `/api/settings/audit-logs/stats/summary` | audit stats |

### Export & health
| Method | Path | |
|--------|------|--|
| GET | `/api/export/xlsx/{domain_id}` | XLSX report (subdomains + vulnerabilities) |
| GET | `/health` | health check (no auth) |

## Errors

Errors return `{ "detail": "…" }` with a standard status code — `400` bad request, `401` unauthenticated, `403` forbidden (e.g. non-admin), `404` not found, `409` conflict, `5xx` server error.
