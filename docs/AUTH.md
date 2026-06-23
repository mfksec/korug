# Authentication & User Management

Subdomain Hunter uses a **multi-layer authentication system** to protect your data:

## 🔐 Authentication Methods

### 1. **User Authentication** (Web Dashboard & API)
Dashboard users authenticate with **username/password** to receive **JWT tokens**.

**Flow:**
```
1. User logs in with username + password
2. Backend validates credentials against database (bcrypt comparison)
3. Server returns JWT access token (1 hour) + refresh token (7 days)
4. Tokens stored in browser localStorage (or secure cookies in production)
5. Subsequent API requests include `Authorization: Bearer <token>` header
6. Logout adds token to revocation blacklist
```

**Endpoint:**
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. **Token Refresh**
Access tokens expire after 1 hour. Use the refresh token to get a new access token **without re-entering credentials**.

**Endpoint:**
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<your_refresh_token>"
}
```

### 3. **API Key Authentication** (Service-to-Service)
For external integrations and scripts, use the `API_KEY` environment variable.

**Setup:**
```bash
export API_KEY="your-secret-api-key"
```

**Usage:**
```http
GET /api/domains/
Authorization: Bearer YOUR_API_KEY
```

---

## 👤 User Management

### Creating Users

**Via CLI (Recommended for local setup):**
```bash
subdomain-hunter create-user
# Prompts for username, email, password, role
```

**Via Web Dashboard:**
Navigate to Settings → User Management (admin only)

### User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full access: create/edit/delete domains, manage users, view audit logs |
| **viewer** | Read-only: view domains, vulnerabilities, scan results |

### CLI User Commands

```bash
# Create a new user
subdomain-hunter create-user

# List all users
subdomain-hunter list-users

# Delete a user
subdomain-hunter delete-user

# Change password
subdomain-hunter change-password
```

---

## 🚀 Initial Setup

### Docker Deployment

When you start the application for the first time, an **admin account is automatically created**:

**Environment Variables** (see `docker/.env.docker`):
```bash
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@subdomain-hunter.local
ADMIN_PASSWORD=  # Leave empty for auto-generated password (logged on first run)
```

**First-run output (check logs):**
```
================================================================================
No ADMIN_PASSWORD set. Created initial admin account:
    username: admin
    password: TrKxL9mN8pQ2vWxYz3jKlMn4oP  (shown once, save this!)
Store this now and change it after first login.
================================================================================
```

### Local Development

```bash
# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/subdomain_hunter"
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000"

# Start the app
python -m subdomain_hunter.run

# In another terminal, create a user
subdomain-hunter create-user
# Enter: username, email, password, role
```

---

## 🔑 Security Best Practices

### Password Security
- ✅ Minimum 8 characters
- ✅ Bcrypt hashing (industry standard)
- ✅ Constant-time comparison (prevents timing attacks)
- ✅ Change default password on first login

### Token Security
- ✅ **Expiration**: Access tokens valid for 1 hour, refresh tokens for 7 days
- ✅ **JTI (JWT ID)**: Each token has a unique ID for revocation tracking
- ✅ **Blacklisting**: Logout immediately invalidates tokens
- ✅ **Redis Backed** (Production): Shared token revocation across all workers
- ✅ **In-Memory Fallback** (Development): Single-process deployments

### API Key Security
- ✅ Store in environment variables (never commit to git)
- ✅ Rotate regularly in production
- ✅ Use different keys for dev/staging/production

### Production Recommendations

**Must Do:**
1. Set strong `JWT_SECRET_KEY` (minimum 32 bytes, cryptographically random)
2. Set strong `ADMIN_PASSWORD` (or save auto-generated password)
3. Change `ALLOWED_ORIGINS` to your actual domain(s)
4. Use HTTPS for all API requests
5. Enable `USE_HTTPONLY_COOKIES=true` for secure cookie storage

**Should Do:**
6. Configure Redis (`REDIS_URL`) for distributed rate limiting & token revocation
7. Implement CSRF protection if using browser cookies
8. Monitor audit logs for suspicious activity
9. Regularly rotate API keys and admin passwords
10. Use VPN/firewall to restrict API access by IP

**Optional:**
11. Implement OAuth2/OpenID Connect for enterprise SSO
12. Use secrets manager (Vault, AWS Secrets Manager) for credential rotation
13. Implement IP-based rate limiting
14. Set up SIEM log aggregation for audit logs

---

## 🔄 Token Flow Diagram

```
User Request
    ↓
Login Endpoint (/api/auth/login)
    ↓ [Validate username/password against DB]
    ↓
Issue Tokens
    ├─ Access Token (1 hour)
    └─ Refresh Token (7 days)
    ↓
Store in Browser (localStorage or httpOnly cookie)
    ↓
Subsequent Requests
    ├─ Include: Authorization: Bearer <access_token>
    ├─ Validation:
    │  ├─ Check JWT signature
    │  ├─ Verify token type ("access")
    │  ├─ Check expiration
    │  ├─ Check JTI not in blacklist
    │  └─ Verify user is active
    ├─ ✅ Token valid → Grant access
    └─ ❌ Token invalid → Return 401 Unauthorized

Token Refresh
    ├─ Send: refresh_token to /api/auth/refresh
    ├─ Validation:
    │  ├─ Check signature
    │  ├─ Verify type ("refresh")
    │  └─ Check not blacklisted
    ├─ ✅ Valid → Issue new access token
    └─ ❌ Invalid → Force re-login

Logout
    ├─ Send request to /api/auth/logout
    ├─ Extract JTI from current token
    ├─ Add JTI to revocation blacklist (Redis or in-memory)
    ├─ Token remains valid until natural expiration, but:
    │  └─ New requests with this token return 401
    └─ User redirected to login page
```

---

## 📚 API Endpoints

### Auth Endpoints

```http
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
```

### Protected Endpoints

All other API endpoints require authentication:

```http
GET    /api/domains/               [List all domains]
POST   /api/domains/               [Create domain]
GET    /api/domains/{id}           [Get domain]
PUT    /api/domains/{id}           [Update domain]
DELETE /api/domains/{id}           [Delete domain]

GET    /api/vulnerabilities/       [List vulnerabilities]
GET    /api/vulnerabilities/{id}   [Get vulnerability]
PUT    /api/vulnerabilities/{id}   [Update vulnerability]
DELETE /api/vulnerabilities/{id}   [Delete vulnerability]

POST   /api/scans/{domain_id}/scan [Trigger scan]
GET    /api/scans/                 [List scan history]

GET    /api/export/domains/{id}    [Export domain report]

GET    /api/audit/                 [List audit logs]

GET    /health                     [Health check (no auth)]
GET    /docs                       [Swagger UI (no auth)]
```

---

## 🐛 Troubleshooting

### "Invalid username or password" on login
- ✅ Check username/email spelling
- ✅ Verify password (spaces, caps, special chars)
- ✅ Confirm user account exists: `subdomain-hunter list-users`

### "Token has expired" error
- ✅ Use the refresh endpoint to get a new access token
- ✅ Or log in again

### "Token not found" or "Invalid token"
- ✅ Ensure token is included in `Authorization` header
- ✅ Format: `Bearer <token>` (with space)
- ✅ Token might have been revoked via logout

### "User no longer exists or is inactive" after logout
- ✅ This is expected! Token was revoked
- ✅ Log in again to get new tokens

### Redis Connection Error
- ✅ If Redis is unavailable, token revocation falls back to in-memory
- ✅ This works for single-process deployment but NOT for multi-worker production
- ✅ Configure `REDIS_URL` to fix: `redis://redis:6379/0`

---

## 📖 See Also

- [API Reference](API.md)
- [CLI Reference](CLI.md)
- [Architecture](ARCHITECTURE.md)
- [Security Guidelines](../SECURITY.md)
