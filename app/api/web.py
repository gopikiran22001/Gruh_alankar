"""Gruha Alankara — Web Scraping API: POST /api/web/search, POST /api/web/scrape"""

from __future__ import annotations
import asyncio, uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.agents.schemas import AgentTask
from app.agents.registry import agent_registry
from app.api.middleware import api_response, rate_limit
from config.constants import AgentName, ScrapingSource

web_bp = Blueprint("web", __name__)

@web_bp.route("/search", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def web_search():
    """Search for products across e-commerce sites."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    agent = agent_registry.get(AgentName.WEB)
    if not agent:
        return api_response(status="error", message="Web agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"web_{uuid.uuid4().hex[:8]}",
        task_type="scrape_products",
        agent_name=AgentName.WEB,
        parameters={
            "query": data.get("query", ""),
            "sources": data.get("sources", ScrapingSource.ALL),
            "max_results": data.get("max_results", 10),
            "category": data.get("category", "furniture"),
        },
        metadata={"user_id": user_id},
    )
    result = asyncio.run(agent.run(task))
    return api_response(data=result.data, metadata={"duration_ms": round(result.duration_ms, 1)})

@web_bp.route("/scrape", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=5, window=60)
def web_scrape():
    """Scrape specific product details."""
    return web_search()  # Same handler, different rate limit
