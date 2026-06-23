"""Slack integration service."""
import json
import logging
from typing import Optional, List

import requests

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SlackIntegration:
    """Service for sending notifications to Slack."""

    def __init__(self):
        self.webhook_url = settings.slack_webhook_url
        self.enabled = settings.slack_enabled and self.webhook_url

    async def send_vulnerability_alert(
        self,
        domain: str,
        subdomain: str,
        vuln_type: str,
        confidence_score: float,
        details: Optional[str] = None,
    ):
        """Send vulnerability alert to Slack."""
        if not self.enabled:
            return
        
        try:
            color = "#ff0000" if confidence_score >= 80 else "#ffcc00"
            
            message = {
                "color": color,
                "title": f"🚨 Vulnerability Detected: {vuln_type}",
                "fields": [
                    {"title": "Domain", "value": domain, "short": True},
                    {"title": "Subdomain", "value": subdomain, "short": True},
                    {"title": "Vulnerability Type", "value": vuln_type, "short": True},
                    {"title": "Confidence Score", "value": f"{confidence_score:.1f}%", "short": True},
                    {"title": "Details", "value": details or "N/A", "short": False},
                ],
            }
            
            response = requests.post(
                self.webhook_url,
                json={"attachments": [message]},
                timeout=10,
            )
            
            if response.status_code != 200:
                logger.error(f"Slack notification failed: {response.text}")
            else:
                logger.info(f"Slack notification sent for {subdomain}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    async def send_new_subdomain_alert(self, domain: str, subdomains: List[str]):
        """Send alert for newly discovered subdomains."""
        if not self.enabled or not subdomains:
            return
        
        try:
            message = {
                "color": "#0099ff",
                "title": f"🆕 New Subdomains Discovered: {domain}",
                "fields": [
                    {"title": "Domain", "value": domain, "short": True},
                    {"title": "Count", "value": str(len(subdomains)), "short": True},
                    {
                        "title": "Subdomains",
                        "value": "\n".join(subdomains[:10]) + (
                            f"\n... and {len(subdomains) - 10} more"
                            if len(subdomains) > 10
                            else ""
                        ),
                        "short": False,
                    },
                ],
            }
            
            response = requests.post(
                self.webhook_url,
                json={"attachments": [message]},
                timeout=10,
            )
            
            if response.status_code != 200:
                logger.error(f"Slack notification failed: {response.text}")
            else:
                logger.info(f"Slack notification sent for new subdomains")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    async def send_scan_summary(
        self,
        domain: str,
        total_subdomains: int,
        new_subdomains: int,
        vulnerabilities_found: int,
        scan_duration: float,
    ):
        """Send scan summary to Slack."""
        if not self.enabled:
            return
        
        try:
            message = {
                "color": "#36a64f",
                "title": f"📊 Scan Summary: {domain}",
                "fields": [
                    {"title": "Domain", "value": domain, "short": True},
                    {"title": "Total Subdomains", "value": str(total_subdomains), "short": True},
                    {"title": "New Subdomains", "value": str(new_subdomains), "short": True},
                    {"title": "Vulnerabilities", "value": str(vulnerabilities_found), "short": True},
                    {"title": "Scan Duration", "value": f"{scan_duration:.1f}s", "short": True},
                ],
            }
            
            response = requests.post(
                self.webhook_url,
                json={"attachments": [message]},
                timeout=10,
            )
            
            if response.status_code != 200:
                logger.error(f"Slack notification failed: {response.text}")
            else:
                logger.info(f"Slack summary sent for {domain}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")


# Create singleton instance
slack_integration = SlackIntegration()
