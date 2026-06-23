# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Körüg                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           User Interfaces                            │  │
│  │  ┌──────────────────┬────────────────┬────────────┐  │  │
│  │  │   FastAPI        │   CLI Tool     │  REST API  │  │  │
│  │  │  /docs /redoc    │  (Click)       │ JSON       │  │  │
│  │  └──────────────────┴────────────────┴────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           API Layer & Routes                         │  │
│  │  /api/domains  /api/scans  /api/vulns  /api/export   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Business Logic (Services)                   │  │
│  │  ┌──────────────┬──────────────┬──────────────────┐ │  │
│  │  │  Discovery   │  Takeover    │  Slack           │ │  │
│  │  │  Service     │  Detection   │  Integration     │ │  │
│  │  └──────────────┴──────────────┴──────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        Data Models (SQLAlchemy ORM)                 │  │
│  │  Domain  Subdomain  Vulnerability  ScanHistory      │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           PostgreSQL Database                        │  │
│  │  • Persistent storage   • Relationships             │  │
│  │  • Historical tracking  • Transactions              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Discovery Service
**File**: `src/korug/services/discovery.py`

Discovers subdomains using multiple passive sources:
- **Subfinder**: Fast enumeration from multiple sources
- **Amass**: Comprehensive passive discovery
- **Shodan.io API**: IP and port data (optional)
- **urlscan.io API**: URL archive lookups (optional)

Features:
- Subprocess integration for CLI tools
- Graceful fallback when API keys missing
- DNS resolution and record collection
- Deduplication across sources

### 2. Takeover Detection Service
**File**: `src/korug/services/takeover_detection.py`

Detects subdomain takeover vulnerabilities:

**S3 Bucket Takeover**
- Detects CNAME pointing to unclaimed S3 buckets
- Uses boto3 for bucket existence verification
- Confidence: 95% (missing), 10-20% (exists)

**CNAME Orphan**
- Identifies CNAMEs pointing to non-existent domains
- Confidence: 85%

**DNS Record Orphans**
- MX records without valid targets
- NS records without valid targets
- Confidence: 80-85%

All findings include confidence scores (0-100%). Only findings ≥75% (configurable) trigger alerts.

### 3. Slack Integration Service
**File**: `src/korug/services/slack_integration.py`

Sends notifications to Slack:
- Vulnerability alerts with details
- New subdomain discovery alerts
- Scan summary reports
- Color-coded by severity

### 4. Data Models
**File**: `src/korug/models/base.py`

Four main models:

**Domain**
```python
- id: int (primary key)
- domain_name: str (unique)
- enabled: bool
- last_scanned: datetime
- created_at: datetime
- updated_at: datetime
- relationships: subdomains, scan_history, vulnerabilities
```

**Subdomain**
```python
- id: int
- domain_id: int (foreign key)
- subdomain: str
- a_records: json
- aaaa_records: json
- cname_record: str
- mx_records: json
- ns_records: json
- first_discovered: datetime
- last_seen: datetime
- relationships: vulnerabilities
```

**Vulnerability**
```python
- id: int
- subdomain_id: int (foreign key)
- domain_id: int (foreign key)
- vuln_type: str (s3_bucket_takeover, cname_orphan, etc.)
- confidence_score: float (0-100)
- details: json
- found_at: datetime
- is_false_positive: bool
- false_positive_reason: str
```

**ScanHistory**
```python
- id: int
- domain_id: int (foreign key)
- scan_timestamp: datetime
- total_subdomains: int
- new_subdomains: int
- vulnerabilities_found: int
- status: str (pending, running, completed, failed)
- error_message: str
- scan_duration_seconds: float
```

### 5. API Layer
**Files**: `src/korug/api/*.py`

RESTful endpoints:
- `domains.py`: Domain CRUD operations
- `scans.py`: Scan triggers and results retrieval
- `vulnerabilities.py`: Vulnerability management
- `export.py`: XLSX export functionality

Features:
- Bearer token authentication
- FastAPI validation and documentation
- HTTP status codes (201, 204, 400, 403, 404, 409, 500)
- Background task support for async operations

### 6. CLI Tool
**File**: `src/korug/cli.py`

Commands using Click framework:
- `add-domain`, `remove-domain`, `list-domains`
- `scan`, `show-results`, `export`
- `config-slack`, `init-database`

### 7. Task Scheduler
**File**: `src/korug/scheduler.py`

APScheduler integration:
- Daily scheduled scans at configurable time
- Automatic domain discovery
- Background task execution

## Data Flow

### 1. Adding a Domain

```
User (CLI/API)
    ↓
add-domain / POST /api/domains/
    ↓
Domain API Handler
    ↓
SQLAlchemy ORM
    ↓
PostgreSQL Database
```

### 2. Scanning a Domain

```
User triggers scan
    ↓
Scan API Handler
    ↓
Background Task
    ├─ Discovery Service
    │  ├─ Subfinder subprocess
    │  ├─ Amass subprocess
    │  ├─ Shodan API (optional)
    │  └─ urlscan API (optional)
    │
    ├─ DNS Resolution
    │  └─ dnspython
    │
    ├─ Store Subdomains in DB
    │
    └─ For each Subdomain:
       ├─ Takeover Detection
       │  ├─ S3 Check (boto3)
       │  ├─ CNAME Orphan Check (DNS)
       │  ├─ DNS Orphan Check (DNS)
       │  └─ Calculate confidence scores
       │
       ├─ Store Vulnerabilities in DB
       │
       └─ Send Slack Notifications (if enabled)
```

### 3. Exporting Results

```
User requests export
    ↓
Export API Handler
    ↓
Query Database
    ├─ Get Subdomains
    └─ Get Vulnerabilities
    ↓
Create XLSX File
    ├─ Sheet 1: Subdomains + DNS records
    └─ Sheet 2: Vulnerabilities
    ↓
Return file to user
```

## Database Schema

```sql
-- Domains table
CREATE TABLE domains (
    id SERIAL PRIMARY KEY,
    domain_name VARCHAR(255) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    last_scanned TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subdomains table
CREATE TABLE subdomains (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    subdomain VARCHAR(255) NOT NULL,
    a_records TEXT,
    aaaa_records TEXT,
    cname_record VARCHAR(255),
    mx_records TEXT,
    ns_records TEXT,
    first_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vulnerabilities table
CREATE TABLE vulnerabilities (
    id SERIAL PRIMARY KEY,
    subdomain_id INTEGER NOT NULL REFERENCES subdomains(id),
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    vuln_type VARCHAR(100) NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    details TEXT,
    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_false_positive BOOLEAN DEFAULT FALSE,
    false_positive_reason TEXT
);

-- Scan history table
CREATE TABLE scan_history (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_subdomains INTEGER DEFAULT 0,
    new_subdomains INTEGER DEFAULT 0,
    vulnerabilities_found INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    scan_duration_seconds FLOAT
);
```

## Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | FastAPI | Web framework |
| ORM | SQLAlchemy | Database layer |
| Database | PostgreSQL | Data persistence |
| CLI | Click | Command-line interface |
| Task Scheduler | APScheduler | Scheduled scans |
| Subdomains | Subfinder, Amass | Discovery tools |
| DNS | dnspython | DNS queries |
| Cloud | boto3 | AWS S3 checks |
| Notifications | Slack SDK | Slack integration |
| Export | openpyxl | XLSX generation |
| Container | Docker | Containerization |

## Security Considerations

1. **API Key Authentication**: Bearer token validation
2. **Environment Variables**: Sensitive data not in code
3. **Database**: Encrypted connections, prepared statements
4. **Subprocess Execution**: Validated command-line arguments
5. **Error Handling**: No stack traces in API responses
6. **CORS**: Configurable for production
7. **Rate Limiting**: Can be added at API layer

## Performance Optimization

1. **Async DNS**: Can use `aiodns` for parallel queries
2. **Parallel Discovery**: Subfinder/Amass run simultaneously
3. **Background Tasks**: Scans don't block API
4. **Database Indexing**: Columns indexed for quick queries
5. **Deduplication**: Prevents duplicate storage
6. **Connection Pooling**: SQLAlchemy connection pool

## Scalability Paths

1. **Horizontal**: Multiple API instances + load balancer
2. **Task Queue**: Celery + Redis for distributed scanning
3. **Database**: Read replicas for scaling read operations
4. **Caching**: Redis cache for DNS queries
5. **Async Workers**: Multiple scan workers for parallel processing
