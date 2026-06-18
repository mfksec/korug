#!/usr/bin/env python
"""Entry point for running the application."""
import uvicorn
import sys
import logging

from subdomain_hunter.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def main():
    """Run the FastAPI application."""
    logger.info(f"Starting Subdomain Hunter on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "subdomain_hunter.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.fastapi_debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
