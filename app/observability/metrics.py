"""Gruha Alankara — Metrics Tracking."""

from __future__ import annotations
import time
from typing import Dict
from config.logging_config import get_logger

logger = get_logger(__name__)

# In-memory counters (for production, use Prometheus/StatsD)
_counters: Dict[str, int] = {}
_histograms: Dict[str, list] = {}


def increment(metric: str, value: int = 1) -> None:
    """Increment a counter metric."""
    _counters[metric] = _counters.get(metric, 0) + value


def record_duration(metric: str, duration_ms: float) -> None:
    """Record a duration for histogram tracking."""
    if metric not in _histograms:
        _histograms[metric] = []
    _histograms[metric].append(duration_ms)
    # Keep last 1000 entries
    if len(_histograms[metric]) > 1000:
        _histograms[metric] = _histograms[metric][-1000:]


def get_metrics() -> Dict:
    """Get all current metrics."""
    return {
        "counters": dict(_counters),
        "histograms": {
            k: {
                "count": len(v),
                "avg_ms": sum(v) / len(v) if v else 0,
                "max_ms": max(v) if v else 0,
                "min_ms": min(v) if v else 0,
            }
            for k, v in _histograms.items()
        },
    }


class Timer:
    """Context manager for timing operations."""

    def __init__(self, metric_name: str):
        self.metric = metric_name
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        duration_ms = (time.time() - self.start) * 1000
        record_duration(self.metric, duration_ms)
