"""
Gruha Alankara — Vision API

POST /api/vision/analyze
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.agents.schemas import AgentTask
from app.agents.registry import agent_registry
from app.api.middleware import api_response, rate_limit
from config.constants import AgentName
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

vision_bp = Blueprint("vision", __name__)


@vision_bp.route("/analyze", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def analyze_room():
    """Analyze a room image."""
    user_id = get_jwt_identity()

    if "image" not in request.files:
        return api_response(status="error", message="Image file required", status_code=400)

    image_file = request.files["image"]
    task_type = request.form.get("task_type", "full_analysis")

    # Save image
    upload_dir = Path(settings.storage.UPLOAD_DIR) / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(image_file.filename).suffix or ".jpg"
    image_path = str(upload_dir / f"{uuid.uuid4().hex[:8]}{ext}")
    image_file.save(image_path)

    # Run vision agent
    vision_agent = agent_registry.get(AgentName.VISION)
    if not vision_agent:
        return api_response(status="error", message="Vision agent unavailable", status_code=503)

    task = AgentTask(
        task_id=f"vision_{uuid.uuid4().hex[:8]}",
        task_type=task_type,
        agent_name=AgentName.VISION,
        parameters={"image_path": image_path},
        metadata={"user_id": user_id},
    )

    result = asyncio.run(vision_agent.run(task))

    return api_response(
        data=result.data,
        metadata={"duration_ms": round(result.duration_ms, 1), "confidence": result.confidence_score},
    )
