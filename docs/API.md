# API Reference

## Base URL
```
http://localhost:8000
```

## Authentication

Subdomain Hunter supports **two authentication methods**:

### 1. **User Authentication** (JWT Tokens)
For dashboard users and most API clients.

**Get a token:**
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
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

**Use the access token:**
```http
GET /api/domains/
Authorization: Bearer <access_token>
```

**Refresh the token (when expired):**
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<refresh_token>"
}
```

### 2. **API Key Authentication**
For service-to-service integrations and scripts.

**Include API key in headers:**
```http
GET /api/domains/
Authorization: Bearer YOUR_API_KEY
```

**Note**: API key is the same `API_KEY` environment variable used for the backend.

---

**For full authentication details**, see [Authentication & User Management](AUTH.md).

## Endpoints

### Authentication

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

#### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<refresh_token>"
}
```

#### Logout
```http
POST /api/auth/logout
Authorization: Bearer <access_token>
```

### Domains

#### Create Domain
```http
POST /api/domains/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "domain_name": "example.com"
}
```

Response:
```json
{
  "id": 1,
  "domain_name": "example.com",
  "enabled": true,
  "last_scanned": null,
  "created_at": "2026-06-18T00:00:00",
  "updated_at": "2026-06-18T00:00:00"
}
```

#### List Domains
```http
GET /api/domains/?skip=0&limit=100
Authorization: Bearer <access_token>
```

#### Get Domain
```http
GET /api/domains/1
Authorization: Bearer <access_token>
```

#### Update Domain
```http
PUT /api/domains/1
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "enabled": false
}
```

#### Delete Domain
```http
DELETE /api/domains/1
Authorization: Bearer <access_token>
```

### Scanning

#### Trigger Scan
```http
POST /api/scans/1/scan
Authorization: Bearer <access_token>
```

Response:
```json
{
  "message": "Scan started for example.com",
  "domain_id": 1
}
```

#### Get Scan Results
```http
GET /api/scans/1/results
Authorization: Bearer YOUR_API_KEY
```

#### Get Scan History
```http
GET /api/scans/history/1?skip=0&limit=100
Authorization: Bearer YOUR_API_KEY
```

### Vulnerabilities

#### List Vulnerabilities
```http
GET /api/vulnerabilities/?domain_id=1&vuln_type=s3_bucket_takeover&skip=0&limit=100
Authorization: Bearer YOUR_API_KEY
```

#### Get Vulnerability
```http
GET /api/vulnerabilities/1
Authorization: Bearer YOUR_API_KEY
```

#### Mark False Positive
```http
PATCH /api/vulnerabilities/1
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "is_false_positive": true,
  "false_positive_reason": "This is a legitimate service"
}
```

#### Delete Vulnerability
```http
DELETE /api/vulnerabilities/1
Authorization: Bearer YOUR_API_KEY
```

### Export

#### Export to XLSX
```http
GET /api/export/xlsx/1
Authorization: Bearer YOUR_API_KEY
```

Returns XLSX file with:
- Sheet 1: Subdomains and DNS records
- Sheet 2: Vulnerabilities

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request"
}
```

### 403 Forbidden
```json
{
  "detail": "Valid API key required"
}
```

### 404 Not Found
```json
{
  "detail": "Domain with id 1 not found"
}
```

### 409 Conflict
```json
{
  "detail": "Domain example.com already exists"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Examples

### Python
```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Add domain
response = requests.post(
    f"{BASE_URL}/api/domains/",
    json={"domain_name": "example.com"},
    headers=headers
)
domain_id = response.json()["id"]

# Trigger scan
response = requests.post(
    f"{BASE_URL}/api/scans/{domain_id}/scan",
    headers=headers
)

# Get results
response = requests.get(
    f"{BASE_URL}/api/scans/{domain_id}/results",
    headers=headers
)
print(response.json())
```

### cURL
```bash
API_KEY="your-api-key"
BASE_URL="http://localhost:8000"

# Add domain
curl -X POST "$BASE_URL/api/domains/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"domain_name": "example.com"}'

# List domains
curl "$BASE_URL/api/domains/" \
  -H "Authorization: Bearer $API_KEY"

# Trigger scan
curl -X POST "$BASE_URL/api/scans/1/scan" \
  -H "Authorization: Bearer $API_KEY"

# Export to XLSX
curl "$BASE_URL/api/export/xlsx/1" \
  -H "Authorization: Bearer $API_KEY" \
  -o report.xlsx
```

### JavaScript
```javascript
const API_KEY = "your-api-key";
const BASE_URL = "http://localhost:8000";

async function listDomains() {
  const response = await fetch(`${BASE_URL}/api/domains/`, {
    headers: { Authorization: `Bearer ${API_KEY}` }
  });
  return response.json();
}

async function addDomain(domainName) {
  const response = await fetch(`${BASE_URL}/api/domains/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`
    },
    body: JSON.stringify({ domain_name: domainName })
  });
  return response.json();
}
```

## Interactive Documentation

Visit `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc) for interactive API documentation where you can try requests directly.
