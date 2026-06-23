"""Package initialization for API routes."""
from korug.api import domains, vulnerabilities, scans, export, alerts, settings, users, integrations

__all__ = [
    "domains", "vulnerabilities", "scans", "export", "alerts",
    "settings", "users", "integrations",
]
