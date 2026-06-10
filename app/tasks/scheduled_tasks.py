"""
Gruha Alankara — Celery Beat Scheduled Tasks
"""

from __future__ import annotations

from app.tasks.celery_app import celery
from config.logging_config import get_logger

logger = get_logger(__name__)


@celery.task(name="app.tasks.scheduled_tasks.discover_trends")
def discover_trends():
    """Daily task to discover trending products and styles."""
    logger.info("scheduled_trend_discovery_started")
    try:
        from app.tasks.agent_tasks import run_web_scraping
        categories = ["sofa", "dining table", "bed", "study desk", "bookshelf"]
        for category in categories:
            run_web_scraping.delay(
                query=f"trending {category} 2025 India",
                max_results=5,
            )
        logger.info("scheduled_trend_discovery_dispatched", categories=len(categories))
    except Exception as e:
        logger.error("scheduled_trend_discovery_failed", error=str(e))


@celery.task(name="app.tasks.scheduled_tasks.cleanup_sessions")
def cleanup_sessions():
    """Hourly task to clean up stale sessions and temp files."""
    logger.info("scheduled_cleanup_started")
    # Redis sessions are self-expiring via TTL
    # Clean up old temp files if needed
    import os
    from pathlib import Path
    from datetime import datetime, timezone, timedelta
    from config.settings import settings

    upload_dir = Path(settings.storage.UPLOAD_DIR)
    if not upload_dir.exists():
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    cleaned = 0
    for file_path in upload_dir.rglob("*"):
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                try:
                    file_path.unlink()
                    cleaned += 1
                except Exception:
                    pass

    logger.info("scheduled_cleanup_completed", files_cleaned=cleaned)
