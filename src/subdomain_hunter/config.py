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
    
    # External APIs (Optional)
    shodan_api_key: Optional[str] = Field(default=None)
    urlscan_api_key: Optional[str] = Field(default=None)
    
    # Scanning Configuration
    scan_schedule_hour: int = Field(default=0)
    scan_schedule_minute: int = Field(default=0)
    confidence_threshold: float = Field(default=75.0)
    
    # AWS
    aws_region: str = Field(default="us-east-1")

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
