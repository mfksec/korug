import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration."""

    # Database - REQUIRED from environment
    database_url: str = Field(
        default=None,
        description="PostgreSQL connection string. Format: postgresql://user:password@host:port/db"
    )
    
    # FastAPI
    fastapi_env: str = Field(default="development")
    fastapi_debug: bool = Field(default_factory=lambda: os.environ.get("FASTAPI_ENV", "development") == "development")
    
    # JWT Secret - REQUIRED from environment
    jwt_secret_key: str = Field(
        default=None,
        description="JWT secret key for token signing. Min 32 bytes. Generate: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
    
    # API Key for API authentication
    api_key: str = Field(
        default=None,
        description="API key for authentication. Generate: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=4)
    
    # CORS - REQUIRED from environment
    allowed_origins: str = Field(
        default=None,
        description="Comma-separated list of allowed CORS origins. Example: http://localhost:3000,http://localhost:5173"
    )
    
    # Slack Integration
    slack_webhook_url: Optional[str] = Field(default=None)
    slack_enabled: bool = Field(default=False)
    
    # Discovery Tools
    subfinder_path: str = Field(default="/usr/local/bin/subfinder")
    amass_path: str = Field(default="/usr/local/bin/amass")
    
    # External APIs (Optional) — free sources need no key; these unlock extra sources.
    shodan_api_key: Optional[str] = Field(default=None)
    urlscan_api_key: Optional[str] = Field(default=None)
    virustotal_api_key: Optional[str] = Field(default=None)
    securitytrails_api_key: Optional[str] = Field(default=None)
    censys_api_id: Optional[str] = Field(default=None)
    censys_api_secret: Optional[str] = Field(default=None)
    binaryedge_api_key: Optional[str] = Field(default=None)

    # Scanning Configuration
    scan_schedule_hour: int = Field(default=0)
    scan_schedule_minute: int = Field(default=0)
    confidence_threshold: float = Field(default=75.0)

    # Recon / enrichment
    enable_auto_discovery: bool = Field(default=True)  # auto-start discovery when a domain is added
    enable_cve_scan: bool = Field(default=True)        # CVE lookup during a manual per-subdomain scan
    enable_auto_cve: bool = Field(default=True)        # incremental CVE lookup during a domain scan (new/changed alive hosts)
    enable_cert_monitoring: bool = Field(default=True) # fetch+store crt.sh certificates during a scan and alert on new certs
    nvd_api_key: str = Field(default="")               # optional NVD API key (raises CVE lookup rate limit)
    enable_http_probe: bool = Field(default=True)      # status/title/tech via HTTP(S)
    enable_subfinder: bool = Field(default=True)       # local subfinder CLI (fast, productive)
    enable_amass: bool = Field(default=False)          # local amass CLI (slow; opt-in, best with API keys)
    enable_port_scan: bool = Field(default=False)      # active port scan (opt-in default)
    port_scan_ports: str = Field(default="21,22,25,53,80,110,143,443,445,3306,3389,5432,6379,8080,8443")
    enrichment_concurrency: int = Field(default=50)    # max concurrent probes/resolves
    http_probe_timeout: int = Field(default=8)         # seconds per probe
    nmap_path: str = Field(default="nmap")             # used for port scan when available
    nmap_service_detection: bool = Field(default=True) # nmap -sV (service/version)
    
    # AWS
    aws_region: str = Field(default="us-east-1")
    
    # Advanced Configuration
    max_discovery_workers: int = Field(default=4)
    api_timeout: int = Field(default=30)
    max_subdomains_per_domain: int = Field(default=10000)
    
    # Security: Rate Limiting
    enable_rate_limiting: bool = Field(default=True)
    login_rate_limit: str = Field(default="5/minute")  # Format: "requests/time_period"
    api_rate_limit: str = Field(default="100/minute")
    
    # Security: httpOnly Cookies (recommended for production)
    use_httponly_cookies: bool = Field(default=False)  # Enable in production
    cookie_secure: bool = Field(default_factory=lambda: os.environ.get("FASTAPI_ENV", "development") != "development")

    # Redis: shared store for rate limiting + token revocation across workers.
    # Leave unset for local single-process development (falls back to in-memory).
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection string for shared rate-limit/revocation state. Example: redis://redis:6379/0",
    )

    # Initial admin user, seeded on first startup if no users exist.
    admin_username: str = Field(default="admin")
    admin_email: str = Field(default="admin@example.com")
    # If left unset, a strong random password is generated and logged once on first run.
    admin_password: Optional[str] = Field(default=None)

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL is set and not hardcoded default."""
        if not v:
            raise ValueError(
                "DATABASE_URL not configured. Set environment variable:\n"
                "export DATABASE_URL='postgresql://user:password@localhost:5432/db'"
            )
        if "subdomain_user:subdomain_password" in v:
            raise ValueError(
                "Default database credentials detected. This is insecure!\n"
                "Set a proper DATABASE_URL with strong credentials."
            )
        return v

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret is set and secure."""
        if not v:
            raise ValueError(
                "JWT_SECRET_KEY not configured. Set environment variable:\n"
                "export JWT_SECRET_KEY='$(python -c \"import secrets; print(secrets.token_urlsafe(32))\")'"
            )
        if len(v) < 32:
            raise ValueError(
                f"JWT_SECRET_KEY must be at least 32 bytes. Current: {len(v)} bytes.\n"
                "Generate new key: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if v.startswith("your-secret"):
            raise ValueError("JWT_SECRET_KEY is using default placeholder. Set a real secret.")
        return v

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key is set."""
        if not v:
            raise ValueError(
                "API_KEY not configured. Set environment variable:\n"
                "export API_KEY='$(python -c \"import secrets; print(secrets.token_urlsafe(32))\")'"
            )
        if v.startswith("your-secret"):
            raise ValueError("API_KEY is using default placeholder. Set a real key.")
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def validate_allowed_origins(cls, v):
        """Validate CORS origins are configured."""
        if not v:
            raise ValueError(
                "ALLOWED_ORIGINS not configured. Set environment variable:\n"
                "export ALLOWED_ORIGINS='http://localhost:3000,http://localhost:5173'"
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
