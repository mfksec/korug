from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


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
