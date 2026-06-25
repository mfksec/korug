from typing import Optional

from pydantic import BaseModel, Field
from datetime import datetime


# User / Auth Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="admin", max_length=32)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserAdminUpdate(BaseModel):
    """Fields an admin may change on another user."""
    email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    role: Optional[str] = Field(default=None, max_length=32)
    is_active: Optional[bool] = None


class ProfileUpdate(BaseModel):
    """Fields a user may change on their own profile."""
    email: str = Field(..., min_length=3, max_length=255)


class PasswordChange(BaseModel):
    """Self-service password change (requires current password)."""
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordReset(BaseModel):
    """Admin-initiated password reset for another user."""
    new_password: str = Field(..., min_length=8, max_length=128)


# Integration Schemas
class SlackConfig(BaseModel):
    enabled: bool = False
    webhook_url: Optional[str] = None


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = True
    from_address: Optional[str] = None
    to_addresses: Optional[str] = None  # comma-separated recipients


class ReconKeysConfig(BaseModel):
    """Source API keys for key-gated discovery providers (set from the UI).

    All optional; omit a field or send the mask sentinel to keep the stored
    value. Stored in the DB and override the env-configured defaults.
    """
    shodan_api_key: Optional[str] = None
    virustotal_api_key: Optional[str] = None
    securitytrails_api_key: Optional[str] = None
    binaryedge_api_key: Optional[str] = None
    urlscan_api_key: Optional[str] = None
    censys_api_id: Optional[str] = None
    censys_api_secret: Optional[str] = None
    nvd_api_key: Optional[str] = None


class IntegrationTestRequest(BaseModel):
    """Optional override config to validate before saving (else use stored)."""
    slack: Optional[SlackConfig] = None
    email: Optional[EmailConfig] = None


# Domain Schemas
class DomainCreate(BaseModel):
    domain_name: str = Field(..., min_length=1, max_length=255)


class DomainUpdate(BaseModel):
    domain_name: Optional[str] = None
    enabled: Optional[bool] = None


class DomainResponse(BaseModel):
    id: int
    domain_name: str
    enabled: bool
    last_scanned: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Subdomain Schemas
class SubdomainCreate(BaseModel):
    subdomain: str
    a_records: Optional[str] = None
    aaaa_records: Optional[str] = None
    cname_record: Optional[str] = None
    mx_records: Optional[str] = None
    ns_records: Optional[str] = None


class SubdomainResponse(BaseModel):
    id: int
    domain_id: int
    subdomain: str
    a_records: Optional[str]
    aaaa_records: Optional[str]
    cname_record: Optional[str]
    mx_records: Optional[str]
    ns_records: Optional[str]
    first_discovered: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


# Vulnerability Schemas
class VulnerabilityCreate(BaseModel):
    subdomain_id: int
    domain_id: int
    vuln_type: str
    confidence_score: float = Field(..., ge=0, le=100)
    details: Optional[str] = None


class VulnerabilityUpdate(BaseModel):
    is_false_positive: bool
    false_positive_reason: Optional[str] = None


class VulnerabilityResponse(BaseModel):
    id: int
    subdomain_id: int
    domain_id: int
    vuln_type: str
    confidence_score: float
    details: Optional[str]
    found_at: datetime
    is_false_positive: bool
    false_positive_reason: Optional[str]

    class Config:
        from_attributes = True


# Scan History Schemas
class ScanHistoryResponse(BaseModel):
    id: int
    domain_id: int
    scan_timestamp: datetime
    total_subdomains: int
    new_subdomains: int
    vulnerabilities_found: int
    status: str
    error_message: Optional[str]
    scan_duration_seconds: Optional[float]

    class Config:
        from_attributes = True


# Scan Results Schema
class ScanResults(BaseModel):
    domain: DomainResponse
    subdomains: list[SubdomainResponse]
    vulnerabilities: list[VulnerabilityResponse]
    scan_history: ScanHistoryResponse
