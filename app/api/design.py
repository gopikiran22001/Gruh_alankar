"""Gruha Alankara — Design API: POST /api/design/generate"""

from __future__ import annotations
import asyncio, uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.agents.schemas import AgentTask
from app.agents.registry import agent_registry
from app.api.middleware import api_response, rate_limit
from config.constants import AgentName

design_bp = Blueprint("design", __name__)

@design_bp.route("/generate", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def generate_design():
    """Generate an interior design proposal."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    agent = agent_registry.get(AgentName.DESIGN)
    if not agent:
        return api_response(status="error", message="Design agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"design_{uuid.uuid4().hex[:8]}",
        task_type=data.get("task_type", "generate_design"),
        agent_name=AgentName.DESIGN,
        parameters={
            "style": data.get("style", "modern"),
            "room_type": data.get("room_type", "living room"),
            "preferences": data.get("preferences", {}),
        },
        constraints={"budget": data.get("budget")},
        context=data.get("context", {}),
        metadata={"user_id": user_id},
    )
    result = asyncio.run(agent.run(task))
    return api_response(data=result.data, metadata={"duration_ms": round(result.duration_ms, 1)})
