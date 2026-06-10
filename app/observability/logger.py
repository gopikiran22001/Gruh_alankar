"""Gruha Alankara — Structured Logger Wrapper."""

from config.logging_config import get_logger as _get_logger
from app.observability.colored_logger import get_colored_logger


def get_logger(name: str):
    """Get a structured logger — re-export from config.logging_config."""
    return _get_logger(name)


__all__ = ["get_logger", "get_colored_logger"]
