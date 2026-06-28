"""Live Certificate Transparency monitoring via certstream.

Connects to a certstream feed (default the public Calidog server) and watches CT
log issuances in near real-time. When a certificate is issued for a **new**
subdomain of a monitored domain, it's recorded as a discovered asset plus a
``subdomain_added`` change — surfacing brand-new attack surface within seconds of
issuance, between scheduled scans.

Opt-in via ``ENABLE_CERTSTREAM``. Self-healing: the consumer reconnects with
exponential backoff and swallows per-message errors so the firehose never crashes
the app. The public Calidog server can be unreliable — set ``CERTSTREAM_URL`` to a
self-hosted instance for production use.
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional

import websockets

from korug.config import get_settings
from korug.db import SessionLocal
from korug.models import Domain, Subdomain, AssetChange

logger = logging.getLogger(__name__)

# Valid-ish hostname guard (mirrors discovery's cleaning).
_APEX_REFRESH_SECONDS = 60


def extract_domains(message: dict) -> List[str]:
    """Pull the certificate's domain names from a certstream message."""
    if (message or {}).get("message_type") != "certificate_update":
        return []
    leaf = (message.get("data") or {}).get("leaf_cert") or {}
    return [d for d in (leaf.get("all_domains") or []) if d]


def match_monitored(all_domains: List[str], apexes: Dict[str, int]) -> Dict[str, int]:
    """Map each CT domain that belongs to a monitored apex → that apex's domain id.

    Wildcards (``*.example.com``) are normalized to the base name. When a name
    matches more than one apex, the most specific (longest) apex wins.
    """
    out: Dict[str, int] = {}
    for raw in all_domains:
        fqdn = (raw or "").strip().lower().removeprefix("*.").rstrip(".")
        if not fqdn:
            continue
        best_apex = None
        for apex in apexes:
            if fqdn == apex or fqdn.endswith("." + apex):
                if best_apex is None or len(apex) > len(best_apex):
                    best_apex = apex
        if best_apex is not None:
            out[fqdn] = apexes[best_apex]
    return out


class CertstreamMonitor:
    """Background consumer of a certstream websocket feed."""

    def __init__(self, url: Optional[str] = None):
        settings = get_settings()
        self.url = url or settings.certstream_url
        self._stop = False
        self._task: Optional[asyncio.Task] = None
        self._apex_cache: Dict[str, int] = {}
        self._apex_loaded_at = 0.0
        # Bounded LRU-ish guard so repeated CT entries for the same name don't
        # hammer the DB; the persistence layer is the source of truth.
        self._seen: set = set()

    # ---- apex cache -------------------------------------------------------

    def _apexes(self) -> Dict[str, int]:
        now = time.time()
        if now - self._apex_loaded_at > _APEX_REFRESH_SECONDS or not self._apex_cache:
            db = SessionLocal()
            try:
                rows = db.query(Domain).filter(Domain.enabled == True).all()  # noqa: E712
                self._apex_cache = {d.domain_name.lower(): d.id for d in rows}
                self._apex_loaded_at = now
            except Exception as e:
                logger.debug("certstream apex refresh failed: %s", e)
            finally:
                db.close()
        return self._apex_cache

    # ---- persistence ------------------------------------------------------

    def _persist(self, matches: Dict[str, int]) -> None:
        """Record any genuinely-new subdomains discovered via CT."""
        db = SessionLocal()
        try:
            for fqdn, domain_id in matches.items():
                if fqdn in self._seen:
                    continue
                self._seen.add(fqdn)
                exists = db.query(Subdomain.id).filter(
                    Subdomain.domain_id == domain_id, Subdomain.subdomain == fqdn,
                ).first()
                if exists:
                    continue
                sub = Subdomain(domain_id=domain_id, subdomain=fqdn, sources="certstream")
                db.add(sub)
                db.flush()
                db.add(AssetChange(
                    domain_id=domain_id, subdomain_id=sub.id,
                    change_type="subdomain_added", target=fqdn,
                    new_value="certstream (CT log)",
                ))
                logger.info("certstream: new subdomain %s", fqdn)
            db.commit()
        except Exception as e:
            logger.warning("certstream persist failed: %s", e)
            db.rollback()
        finally:
            db.close()
        # Keep the dedup set from growing without bound.
        if len(self._seen) > 50000:
            self._seen.clear()

    # ---- consume loop -----------------------------------------------------

    async def _on_message(self, raw) -> None:
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            return
        domains = extract_domains(msg)
        if not domains:
            return
        apexes = self._apexes()
        if not apexes:
            return
        matches = match_monitored(domains, apexes)
        if matches:
            await asyncio.to_thread(self._persist, matches)

    async def run(self) -> None:
        backoff = 1
        while not self._stop:
            try:
                async with websockets.connect(self.url, ping_interval=20, max_size=2 ** 22) as ws:
                    logger.info("certstream connected: %s", self.url)
                    backoff = 1
                    async for raw in ws:
                        if self._stop:
                            break
                        await self._on_message(raw)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._stop:
                    break
                logger.warning("certstream connection error: %s (retry in %ss)", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
        logger.info("certstream monitor stopped")

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop = False
            self._task = asyncio.create_task(self.run())
            logger.info("certstream monitor starting (%s)", self.url)

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None


_monitor: Optional[CertstreamMonitor] = None


def start_certstream() -> None:
    """Start the certstream consumer if enabled (called from app startup)."""
    settings = get_settings()
    if not settings.enable_certstream:
        return
    global _monitor
    if _monitor is None:
        _monitor = CertstreamMonitor()
    _monitor.start()


async def stop_certstream() -> None:
    if _monitor is not None:
        await _monitor.stop()
