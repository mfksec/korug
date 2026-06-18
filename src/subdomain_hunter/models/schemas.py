from typing import Optional

from pydantic import BaseModel, Field
from datetime import datetime


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
