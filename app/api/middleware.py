"""
Gruha Alankara — API Middleware

Request/response logging, request ID injection, and rate limiting.
"""

from __future__ import annotations

import time
import uuid
from functools import wraps
from typing import Any, Callable

from flask import g, jsonify, request

from app.database.redis_cache import cache
from config.logging_config import get_logger

logger = get_logger(__name__)


def inject_request_id() -> None:
    """Inject a unique request ID into Flask's g object."""
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    g.start_time = time.time()


def log_request() -> None:
    """Log incoming request details."""
    logger.info(
        "request_received",
        request_id=getattr(g, "request_id", ""),
        method=request.method,
        path=request.path,
        remote_addr=request.remote_addr,
    )


def log_response(response):
    """Log response details."""
    duration_ms = (time.time() - getattr(g, "start_time", time.time())) * 1000
    logger.info(
        "request_completed",
        request_id=getattr(g, "request_id", ""),
        status=response.status_code,
        duration_ms=round(duration_ms, 1),
    )
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    response.headers["X-Response-Time"] = f"{round(duration_ms, 1)}ms"
    return response


def rate_limit(max_requests: int = 60, window: int = 60):
    """
    Rate limiting decorator using Redis.

    Args:
        max_requests: Max requests per window.
        window: Window duration in seconds.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any):
            # Use user ID if authenticated, else IP
            from flask_jwt_extended import get_jwt_identity
            try:
                identifier = get_jwt_identity() or request.remote_addr
            except Exception:
                identifier = request.remote_addr

            allowed, remaining = cache.check_rate_limit(
                identifier=f"{identifier}:{request.endpoint}",
                max_requests=max_requests,
                window_seconds=window,
            )

            if not allowed:
                return jsonify({
                    "status": "error",
                    "error": "rate_limited",
                    "message": "Too many requests. Please try again later.",
                }), 429

            response = f(*args, **kwargs)
            return response

        return decorated
    return decorator


def api_response(
    data: Any = None,
    message: str = "",
    status: str = "success",
    status_code: int = 200,
    metadata: dict = None,
):
    """Standard API response envelope."""
    body = {"status": status}

    if message:
        body["message"] = message

    if data is not None:
        body["data"] = data

    if metadata:
        body["metadata"] = metadata

    body["request_id"] = getattr(g, "request_id", "")

    return jsonify(body), status_code
