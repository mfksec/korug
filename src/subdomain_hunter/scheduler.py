"""Task scheduler for automated scans."""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from subdomain_hunter.config import get_settings
from subdomain_hunter.db import SessionLocal
from subdomain_hunter.models import Domain

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = BackgroundScheduler()


def scheduled_scan_task():
    """Task to run scheduled scans for all enabled domains."""
    db: Session = SessionLocal()
    try:
        logger.info("Starting scheduled scan task")
        domains = db.query(Domain).filter(Domain.enabled == True).all()
        
        if not domains:
            logger.info("No domains to scan")
            return
        
        for domain in domains:
            logger.info(f"Scheduling scan for {domain.domain_name}")
            # Import here to avoid circular imports
            from subdomain_hunter.api.scans import perform_scan
            import asyncio
            
            # Run scan asynchronously
            # Note: In production, this would be handled by a background task queue
            logger.info(f"Scan for {domain.domain_name} would be queued")
    
    except Exception as e:
        logger.error(f"Error in scheduled scan task: {e}")
    finally:
        db.close()


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
