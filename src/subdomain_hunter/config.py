from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration."""

    # Database
    database_url: str = "postgresql://subdomain_user:subdomain_password@localhost:5432/subdomain_hunter"
    
    # FastAPI
    fastapi_env: str = "development"
    fastapi_debug: bool = True
    api_key: str = "your-secret-api-key-here"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Slack Integration
    slack_webhook_url: Optional[str] = None
    slack_enabled: bool = False
    
    # Discovery Tools
    subfinder_path: str = "/usr/local/bin/subfinder"
    amass_path: str = "/usr/local/bin/amass"
    
    # External APIs (Optional)
    shodan_api_key: Optional[str] = None
    urlscan_api_key: Optional[str] = None
    
    # Scanning Configuration
    scan_schedule_hour: int = 0
    scan_schedule_minute: int = 0
    confidence_threshold: float = 75.0
    
    # AWS
    aws_region: str = "us-east-1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
