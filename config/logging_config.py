"""
Gruha Alankara — Logging Configuration
Structured logging using structlog with JSON output for production
and colored console output for development.
"""

from __future__ import annotations

import logging
import sys

import structlog

from config.settings import settings


def setup_logging() -> None:
    """
    Configure structlog and stdlib logging for the application.
    - In production (LOG_FORMAT=json): JSON-formatted logs for ELK/CloudWatch
    - In development: colored, human-readable console output
    """
    log_level = getattr(logging, settings.logging.LEVEL.upper(), logging.INFO)
    is_json = settings.logging.FORMAT.lower() == "json"

    # Shared processors for all log entries
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_json:
        # Production: JSON output
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the stdlib root logger
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers
    for noisy_logger in [
        "urllib3",
        "httpx",
        "httpcore",
        "chromadb",
        "pymongo",
        "celery",
        "werkzeug",
        "playwright",
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger bound to the given name.

    Usage:
        logger = get_logger(__name__)
        logger.info("processing request", user_id="abc123", action="analyze")
    """
    return structlog.get_logger(name)
