"""Package initialization for API routes."""
from subdomain_hunter.api import domains, vulnerabilities, scans, export, alerts, settings

__all__ = ["domains", "vulnerabilities", "scans", "export", "alerts", "settings"]
