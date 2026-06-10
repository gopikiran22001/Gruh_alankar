"""Gruha Alankara — Structured Logger Wrapper."""

from config.logging_config import get_logger as _get_logger


def get_logger(name: str):
    """Get a structured logger — re-export from config.logging_config."""
    return _get_logger(name)
