from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User model - represents an authenticated dashboard/API user."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default="admin", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Domain(Base):
    """Domain model - represents a domain to monitor."""
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    domain_name = Column(String(255), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    last_scanned = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subdomains = relationship("Subdomain", back_populates="domain", cascade="all, delete-orphan")
    scan_history = relationship("ScanHistory", back_populates="domain", cascade="all, delete-orphan")
    vulnerabilities = relationship("Vulnerability", back_populates="domain", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Domain(id={self.id}, domain_name={self.domain_name})>"


class Subdomain(Base):
    """Subdomain model - represents discovered subdomains."""
    __tablename__ = "subdomains"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False, index=True)
    subdomain = Column(String(255), nullable=False, index=True)
    
    # DNS Records
    a_records = Column(Text, nullable=True)  # JSON array of A records
    aaaa_records = Column(Text, nullable=True)  # JSON array of AAAA records
    cname_record = Column(String(255), nullable=True)
    mx_records = Column(Text, nullable=True)  # JSON array of MX records
    ns_records = Column(Text, nullable=True)  # JSON array of NS records
    
    # Status and timestamps
    first_discovered = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="subdomains")
    vulnerabilities = relationship("Vulnerability", back_populates="subdomain", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Subdomain(id={self.id}, subdomain={self.subdomain})>"


class Vulnerability(Base):
    """Vulnerability model - represents detected vulnerabilities."""
    __tablename__ = "vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    subdomain_id = Column(Integer, ForeignKey("subdomains.id"), nullable=False, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False, index=True)
    
    # Vulnerability details
    vuln_type = Column(String(100), nullable=False, index=True)  # e.g., "s3_bucket", "cname_orphan", "dns_orphan"
    confidence_score = Column(Float, default=0.0)  # 0-100
    details = Column(Text, nullable=True)  # JSON or detailed description
    
    # Status tracking
    found_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_false_positive = Column(Boolean, default=False)
    false_positive_reason = Column(Text, nullable=True)
    
    # Relationships
    subdomain = relationship("Subdomain", back_populates="vulnerabilities")
    domain = relationship("Domain", back_populates="vulnerabilities")

    def __repr__(self) -> str:
        return f"<Vulnerability(id={self.id}, vuln_type={self.vuln_type}, confidence={self.confidence_score})>"


class ScanHistory(Base):
    """ScanHistory model - tracks scan execution history."""
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False, index=True)

    # Scan details
    scan_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_subdomains = Column(Integer, default=0)
    new_subdomains = Column(Integer, default=0)
    vulnerabilities_found = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)

    # Performance metrics
    scan_duration_seconds = Column(Float, nullable=True)

    # Relationships
    domain = relationship("Domain", back_populates="scan_history")

    def __repr__(self) -> str:
        return f"<ScanHistory(id={self.id}, domain_id={self.domain_id}, status={self.status})>"


class Alert(Base):
    """Alert model - security alerts generated from scan findings."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=True, index=True)
    vulnerability_id = Column(Integer, ForeignKey("vulnerabilities.id"), nullable=True, index=True)

    # Display name of the affected domain/subdomain
    target = Column(String(255), nullable=False)
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    message = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    is_resolved = Column(Boolean, default=False, index=True)

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, target={self.target}, severity={self.severity})>"


class ApiKey(Base):
    """ApiKey model - programmatic access keys for a user."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)  # hash of the full secret
    key_display = Column(String(64), nullable=False)  # masked, e.g. sk-****abcd1234
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, active={self.is_active})>"


class UserSetting(Base):
    """UserSetting model - per-user dashboard preferences."""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    theme = Column(String(20), default="light")
    notifications_enabled = Column(Boolean, default=True)
    email_alerts = Column(Boolean, default=True)
    scan_frequency = Column(String(20), default="daily")
    export_format = Column(String(20), default="json")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserSetting(id={self.id}, user_id={self.user_id})>"


class IntegrationConfig(Base):
    """IntegrationConfig model - persisted config for an external integration.

    One row per provider (e.g. "slack", "email"). Settings are stored as a JSON
    blob so each provider can keep its own shape; secrets live in the same blob
    and are masked on read by the API layer.
    """
    __tablename__ = "integration_configs"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    config = Column(Text, nullable=True)  # JSON-encoded provider settings
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<IntegrationConfig(provider={self.provider}, enabled={self.enabled})>"


class AuditLog(Base):
    """AuditLog model - persistent record of security audit events."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(255), nullable=True, index=True)
    event = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    status = Column(String(20), default="success")
    details = Column(Text, nullable=True)  # JSON-encoded details
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event={self.event}, user={self.user})>"
