"""Integrations API - configure & test Slack and Email notifications.

Config is persisted in the integration_configs table (one row per provider).
Secrets (Slack webhook URL, SMTP password) are never returned in full; reads
expose only a boolean "configured" flag and a masked preview. Writes that omit
a secret (or send the mask sentinel) preserve the stored value.
"""
import json
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import require_role, get_current_user
from korug.audit import log_audit_event, AuditEvent
from korug.config import get_settings
from korug.models import IntegrationConfig, SlackConfig, EmailConfig, ReconKeysConfig
from korug.services import email_integration

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

MASK = "********"

# Source API keys for key-gated discovery providers, stored under one row.
RECON_FIELDS = [
    "shodan_api_key", "virustotal_api_key", "securitytrails_api_key",
    "binaryedge_api_key", "urlscan_api_key", "censys_api_id", "censys_api_secret",
    "nvd_api_key",
]


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load(db: Session, provider: str) -> dict:
    """Load stored config for a provider as a dict (env defaults applied)."""
    row = db.query(IntegrationConfig).filter(IntegrationConfig.provider == provider).first()
    stored = json.loads(row.config) if row and row.config else {}

    if provider == "slack":
        return {
            "enabled": row.enabled if row else bool(settings.slack_enabled),
            "webhook_url": stored.get("webhook_url") or settings.slack_webhook_url or "",
        }
    if provider == "email":
        return {
            "enabled": row.enabled if row else False,
            "smtp_host": stored.get("smtp_host", ""),
            "smtp_port": stored.get("smtp_port", 587),
            "smtp_user": stored.get("smtp_user", ""),
            "smtp_password": stored.get("smtp_password", ""),
            "use_tls": stored.get("use_tls", True),
            "from_address": stored.get("from_address", ""),
            "to_addresses": stored.get("to_addresses", ""),
        }
    if provider == "recon_keys":
        env_defaults = {
            "shodan_api_key": settings.shodan_api_key,
            "virustotal_api_key": settings.virustotal_api_key,
            "securitytrails_api_key": settings.securitytrails_api_key,
            "binaryedge_api_key": settings.binaryedge_api_key,
            "urlscan_api_key": settings.urlscan_api_key,
            "censys_api_id": settings.censys_api_id,
            "censys_api_secret": settings.censys_api_secret,
            "nvd_api_key": settings.nvd_api_key,
        }
        return {f: (stored.get(f) or env_defaults.get(f) or "") for f in RECON_FIELDS}
    return stored


def _recon_public(cfg: dict) -> dict:
    """Masked view: per key, a *_configured flag and a masked placeholder."""
    out: dict = {}
    for f in RECON_FIELDS:
        out[f"{f}_configured"] = bool(cfg.get(f))
        out[f] = MASK if cfg.get(f) else ""
    return out


def get_recon_keys(db: Session) -> dict:
    """Internal: DB-stored source keys mapped to discovery's expected names.

    Returns only stored values (empty when unset); discovery merges env defaults.
    """
    row = db.query(IntegrationConfig).filter(IntegrationConfig.provider == "recon_keys").first()
    stored = json.loads(row.config) if row and row.config else {}
    return {
        "shodan": stored.get("shodan_api_key") or "",
        "virustotal": stored.get("virustotal_api_key") or "",
        "securitytrails": stored.get("securitytrails_api_key") or "",
        "binaryedge": stored.get("binaryedge_api_key") or "",
        "urlscan": stored.get("urlscan_api_key") or "",
        "censys_id": stored.get("censys_api_id") or "",
        "censys_secret": stored.get("censys_api_secret") or "",
        "nvd": stored.get("nvd_api_key") or "",
    }


def _save(db: Session, provider: str, cfg: dict, user: str) -> None:
    row = db.query(IntegrationConfig).filter(IntegrationConfig.provider == provider).first()
    if not row:
        row = IntegrationConfig(provider=provider)
    row.enabled = bool(cfg.get("enabled", False))
    row.config = json.dumps(cfg)
    row.updated_by = user
    db.add(row)
    db.commit()


def _slack_public(cfg: dict) -> dict:
    return {
        "enabled": cfg["enabled"],
        "webhook_configured": bool(cfg.get("webhook_url")),
        "webhook_url": MASK if cfg.get("webhook_url") else "",
    }


def _email_public(cfg: dict) -> dict:
    return {
        "enabled": cfg["enabled"],
        "smtp_host": cfg.get("smtp_host", ""),
        "smtp_port": cfg.get("smtp_port", 587),
        "smtp_user": cfg.get("smtp_user", ""),
        "password_configured": bool(cfg.get("smtp_password")),
        "smtp_password": MASK if cfg.get("smtp_password") else "",
        "use_tls": cfg.get("use_tls", True),
        "from_address": cfg.get("from_address", ""),
        "to_addresses": cfg.get("to_addresses", ""),
    }


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@router.get("/")
def get_integrations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return current integration config with secrets masked."""
    return {
        "slack": _slack_public(_load(db, "slack")),
        "email": _email_public(_load(db, "email")),
        "recon_keys": _recon_public(_load(db, "recon_keys")),
    }


@router.put("/recon-keys")
def update_recon_keys(
    body: ReconKeysConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Update source API keys. Omit/mask a field to keep the stored value."""
    current = _load(db, "recon_keys")
    incoming = body.dict()
    cfg: dict = {}
    for f in RECON_FIELDS:
        val = incoming.get(f)
        cfg[f] = current.get(f, "") if val in (None, "", MASK) else val
    cfg["enabled"] = any(cfg.get(f) for f in RECON_FIELDS)
    _save(db, "recon_keys", cfg, current_user["sub"])
    log_audit_event(
        AuditEvent.INTEGRATION_UPDATED, user=current_user["sub"],
        resource_type="integration", resource_id="recon_keys",
        details={"configured": [f for f in RECON_FIELDS if cfg.get(f)]},
    )
    return _recon_public(cfg)


# ---------------------------------------------------------------------------
# Update (admin only)
# ---------------------------------------------------------------------------

@router.put("/slack")
def update_slack(
    body: SlackConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Update Slack config. Omit/mask webhook_url to keep the stored value."""
    current = _load(db, "slack")
    webhook = body.webhook_url
    if webhook in (None, "", MASK):
        webhook = current.get("webhook_url", "")

    cfg = {"enabled": body.enabled, "webhook_url": webhook}
    _save(db, "slack", cfg, current_user["sub"])
    log_audit_event(
        AuditEvent.INTEGRATION_UPDATED, user=current_user["sub"],
        resource_type="integration", resource_id="slack",
        details={"enabled": body.enabled},
    )
    return _slack_public(cfg)


@router.put("/email")
def update_email(
    body: EmailConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Update Email/SMTP config. Omit/mask smtp_password to keep stored value."""
    current = _load(db, "email")
    password = body.smtp_password
    if password in (None, "", MASK):
        password = current.get("smtp_password", "")

    cfg = {
        "enabled": body.enabled,
        "smtp_host": body.smtp_host or "",
        "smtp_port": body.smtp_port,
        "smtp_user": body.smtp_user or "",
        "smtp_password": password,
        "use_tls": body.use_tls,
        "from_address": body.from_address or "",
        "to_addresses": body.to_addresses or "",
    }
    _save(db, "email", cfg, current_user["sub"])
    log_audit_event(
        AuditEvent.INTEGRATION_UPDATED, user=current_user["sub"],
        resource_type="integration", resource_id="email",
        details={"enabled": body.enabled, "smtp_host": cfg["smtp_host"]},
    )
    return _email_public(cfg)


# ---------------------------------------------------------------------------
# Test (admin only) - uses stored config
# ---------------------------------------------------------------------------

@router.post("/slack/test")
def test_slack(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Send a test message to the configured Slack webhook."""
    cfg = _load(db, "slack")
    webhook = cfg.get("webhook_url")
    if not webhook:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No Slack webhook configured")

    log_audit_event(
        AuditEvent.INTEGRATION_TESTED, user=current_user["sub"],
        resource_type="integration", resource_id="slack",
    )
    try:
        resp = requests.post(
            webhook,
            json={"text": "✅ Körüg test notification — your Slack integration is working."},
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Slack returned {resp.status_code}: {resp.text[:200]}",
            )
    except requests.RequestException as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not reach Slack: {e}")

    return {"status": "sent", "message": "Test message delivered to Slack"}


@router.post("/email/test")
def test_email(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Send a test email using the stored SMTP config."""
    cfg = _load(db, "email")
    log_audit_event(
        AuditEvent.INTEGRATION_TESTED, user=current_user["sub"],
        resource_type="integration", resource_id="email",
    )
    try:
        email_integration.send_test_email(cfg)
    except email_integration.EmailConfigError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:  # smtplib / socket errors
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Failed to send email: {e}")

    return {"status": "sent", "message": f"Test email sent to {cfg.get('to_addresses')}"}
