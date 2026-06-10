"""Gruha Alankara — Booking API: POST /api/booking/create"""

from __future__ import annotations
import asyncio, uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.agents.schemas import AgentTask
from app.agents.registry import agent_registry
from app.api.middleware import api_response, rate_limit
from config.constants import AgentName

booking_bp = Blueprint("booking", __name__)

@booking_bp.route("/create", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def create_booking():
    """Create a product booking."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    agent = agent_registry.get(AgentName.BOOKING)
    if not agent:
        return api_response(status="error", message="Booking agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"book_{uuid.uuid4().hex[:8]}",
        task_type="create_booking",
        agent_name=AgentName.BOOKING,
        parameters={
            "user_id": user_id,
            "products": data.get("products", []),
            "payment_info": data.get("payment_info", {}),
            "delivery_address": data.get("delivery_address", {}),
            "project_id": data.get("project_id"),
        },
        metadata={"user_id": user_id},
    )
    result = asyncio.run(agent.run(task))
    
    # If booking created successfully, fetch the full booking details
    if result.is_success and result.data.get("booking_id"):
        from app.database.mongo import find_by_id
        from config.constants import MongoCollection
        
        booking_id = result.data.get("booking_id")
        full_booking = find_by_id(MongoCollection.BOOKINGS, booking_id)
        
        if full_booking:
            # Add the full booking details to the response
            result.data["booking"] = full_booking
    
    status_code = 201 if result.is_success else 400
    return api_response(data=result.data, status_code=status_code)


@booking_bp.route("/track/<booking_id>", methods=["GET"])
@jwt_required()
def track_booking(booking_id: str):
    """Track a booking."""
    agent = agent_registry.get(AgentName.BOOKING)
    if not agent:
        return api_response(status="error", message="Booking agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"track_{uuid.uuid4().hex[:8]}",
        task_type="track_order",
        agent_name=AgentName.BOOKING,
        parameters={"booking_id": booking_id},
    )
    result = asyncio.run(agent.run(task))
    return api_response(data=result.data)


@booking_bp.route("/list", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=20, window=60)
def list_bookings():
    """List all bookings for the current user."""
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()
    status_filter = request.args.get("status")

    agent = agent_registry.get(AgentName.BOOKING)
    if not agent:
        return api_response(status="error", message="Booking agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"list_{uuid.uuid4().hex[:8]}",
        task_type="list_bookings",
        agent_name=AgentName.BOOKING,
        parameters={"user_id": user_id, "status": status_filter},
    )
    result = asyncio.run(agent.run(task))
    return api_response(data=result.data)
