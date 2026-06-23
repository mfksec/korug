"""Email (SMTP) integration service.

Stateless senders that take an explicit config dict so the same code path is
used for "send a test now" and for real alert notifications. Config is sourced
from the database (see korug.api.integrations), with environment defaults.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


class EmailConfigError(ValueError):
    """Raised when the supplied email configuration is incomplete."""


def _recipients(cfg: dict) -> list[str]:
    raw = cfg.get("to_addresses") or ""
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def validate_config(cfg: dict) -> None:
    """Validate that a config dict has everything needed to send mail."""
    missing = [k for k in ("smtp_host", "from_address") if not cfg.get(k)]
    if missing:
        raise EmailConfigError(f"Missing required email settings: {', '.join(missing)}")
    if not _recipients(cfg):
        raise EmailConfigError("At least one recipient (to_addresses) is required")


def send_email(cfg: dict, subject: str, body: str, html: Optional[str] = None) -> None:
    """Send an email using the supplied SMTP config. Raises on failure."""
    validate_config(cfg)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_address"]
    msg["To"] = ", ".join(_recipients(cfg))
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    host = cfg["smtp_host"]
    port = int(cfg.get("smtp_port") or 587)
    user = cfg.get("smtp_user")
    password = cfg.get("smtp_password")
    use_tls = bool(cfg.get("use_tls", True))

    timeout = 15
    if port == 465:
        # Implicit TLS
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as server:
            if user:
                server.login(user, password or "")
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.ehlo()
            if use_tls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if user:
                server.login(user, password or "")
            server.send_message(msg)

    logger.info("Email sent to %s via %s:%s", msg["To"], host, port)


def send_test_email(cfg: dict) -> None:
    """Send a verification email to confirm the configuration works."""
    send_email(
        cfg,
        subject="Körüg test notification",
        body=(
            "This is a test email from Körüg.\n\n"
            "If you received this, your email integration is configured correctly."
        ),
        html=(
            "<h2>Körüg test notification ✅</h2>"
            "<p>If you received this, your email integration is configured correctly.</p>"
        ),
    )


def send_vulnerability_alert(
    cfg: dict,
    domain: str,
    subdomain: str,
    vuln_type: str,
    confidence_score: float,
    details: Optional[str] = None,
) -> None:
    """Send a vulnerability alert email using the supplied config."""
    subject = f"[Körüg] {vuln_type} on {subdomain} ({confidence_score:.0f}%)"
    body = (
        f"Vulnerability detected\n\n"
        f"Domain: {domain}\n"
        f"Subdomain: {subdomain}\n"
        f"Type: {vuln_type}\n"
        f"Confidence: {confidence_score:.1f}%\n"
        f"Details: {details or 'N/A'}\n"
    )
    send_email(cfg, subject, body)
