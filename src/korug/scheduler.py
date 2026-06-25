"""Task scheduler for automated scans."""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from korug.config import get_settings
from korug.db import SessionLocal
from korug.models import Domain

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = BackgroundScheduler()


def scheduled_scan_task():
    """Continuous monitoring: re-run discovery for every enabled domain.

    Runs in the scheduler's background thread, so each domain gets a fresh DB
    session and its own event loop via ``asyncio.run``.
    """
    import asyncio
    from korug.api.scans import perform_scan

    db: Session = SessionLocal()
    try:
        domain_ids = [d.id for d in db.query(Domain).filter(Domain.enabled == True).all()]
    finally:
        db.close()

    if not domain_ids:
        logger.info("Scheduled re-discovery: no enabled domains")
        return

    logger.info("Scheduled re-discovery for %d domain(s)", len(domain_ids))
    for did in domain_ids:
        session = SessionLocal()
        try:
            asyncio.run(perform_scan(did, session, False))
        except Exception as e:
            logger.error("Scheduled re-discovery failed for domain %s: %s", did, e)
        finally:
            session.close()


def start_scheduler():
    """Start the background scheduler."""
    try:
        # Schedule scans daily at configured time
        hour = settings.scan_schedule_hour
        minute = settings.scan_schedule_minute
        
        scheduler.add_job(
            scheduled_scan_task,
            "cron",
            hour=hour,
            minute=minute,
            id="daily_scan",
            name="Daily subdomain scan",
        )
        
        if not scheduler.running:
            scheduler.start()
            logger.info(f"Scheduler started - daily scans at {hour:02d}:{minute:02d}")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")


def stop_scheduler():
    """Stop the background scheduler."""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
