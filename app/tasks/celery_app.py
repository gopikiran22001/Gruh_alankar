"""
Gruha Alankara — Celery Configuration
"""

from __future__ import annotations

from celery import Celery

from config.settings import settings

celery = Celery(
    "gruha_alankara",
    broker=settings.celery.BROKER_URL,
    backend=settings.celery.RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # soft limit at 9 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.agent_tasks.run_workflow": {"queue": "default"},
        "app.tasks.agent_tasks.run_vision_analysis": {"queue": "vision"},
        "app.tasks.agent_tasks.run_voice_synthesis": {"queue": "voice"},
        "app.tasks.agent_tasks.run_web_scraping": {"queue": "web_scraping"},
    },
    beat_schedule={
        "discover-trends-daily": {
            "task": "app.tasks.scheduled_tasks.discover_trends",
            "schedule": 86400.0,  # every 24 hours
        },
        "cleanup-stale-sessions": {
            "task": "app.tasks.scheduled_tasks.cleanup_sessions",
            "schedule": 3600.0,  # every hour
        },
    },
)
