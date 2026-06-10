"""Gruha Alankara — Furniture API: POST /api/furniture/search"""

from __future__ import annotations
import asyncio, uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.agents.schemas import AgentTask
from app.agents.registry import agent_registry
from app.api.middleware import api_response, rate_limit
from config.constants import AgentName

furniture_bp = Blueprint("furniture", __name__)

@furniture_bp.route("/search", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=15, window=60)
def search_furniture():
    """Search and recommend furniture."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    agent = agent_registry.get(AgentName.FURNITURE)
    if not agent:
        return api_response(status="error", message="Furniture agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"furn_{uuid.uuid4().hex[:8]}",
        task_type=data.get("task_type", "recommend_products"),
        agent_name=AgentName.FURNITURE,
        parameters={
            "style": data.get("style", "modern"),
            "room_type": data.get("room_type", "living room"),
            "products": data.get("products", []),
            "criteria": data.get("criteria", ["price", "quality", "style_match"]),
        },
        constraints={"budget": data.get("budget")},
        context=data.get("context", {}),
        metadata={"user_id": user_id},
    )
    result = asyncio.run(agent.run(task))
    return api_response(data=result.data, metadata={"duration_ms": round(result.duration_ms, 1)})
