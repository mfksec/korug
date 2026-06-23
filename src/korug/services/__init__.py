"""Package initialization for services."""
from subdomain_hunter.services.discovery import discovery_service
from subdomain_hunter.services.takeover_detection import takeover_detector

__all__ = ["discovery_service", "takeover_detector"]
