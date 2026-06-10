"""Gruha Alankara — Agent Execution Logger."""

from __future__ import annotations
from typing import Any, Dict, Optional
from app.database.mongo import log_agent_execution as _log_to_mongo
from app.observability.metrics import increment, record_duration
from config.logging_config import get_logger

logger = get_logger(__name__)


def log_agent_run(
    workflow_id: str,
    agent_name: str,
    task_type: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    status: str,
    duration_ms: float,
    error: Optional[str] = None,
) -> None:
    """Log agent execution to both MongoDB and metrics."""
    # MongoDB
    try:
        _log_to_mongo(workflow_id, agent_name, task_type, input_data, output_data, status, duration_ms, error)
    except Exception as e:
        logger.warning("agent_log_mongo_failed", error=str(e))

    # Metrics
    increment(f"agent.{agent_name}.calls")
    increment(f"agent.{agent_name}.{status}")
    record_duration(f"agent.{agent_name}.duration", duration_ms)

    if error:
        increment(f"agent.{agent_name}.errors")
