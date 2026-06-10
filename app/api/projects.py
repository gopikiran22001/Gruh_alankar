"""Gruha Alankara — Projects API: GET /api/projects, POST /api/projects"""

from __future__ import annotations
import uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.api.middleware import api_response, rate_limit
from app.database.mongo import insert_one, find_many, find_by_id
from config.constants import MongoCollection

projects_bp = Blueprint("projects", __name__)

@projects_bp.route("/projects", methods=["GET"])
@jwt_required()
def list_projects():
    """List user's projects."""
    user_id = get_jwt_identity()
    limit = request.args.get("limit", 20, type=int)
    skip = request.args.get("skip", 0, type=int)
    projects = find_many(
        MongoCollection.PROJECTS,
        {"user_id": user_id},
        sort=[("created_at", -1)],
        limit=limit,
        skip=skip,
    )
    return api_response(data={"projects": projects, "total": len(projects)})

@projects_bp.route("/projects", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def create_project():
    """Create a new design project."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    project = {
        "user_id": user_id,
        "name": data.get("name", "Untitled Project"),
        "description": data.get("description", ""),
        "room_type": data.get("room_type", ""),
        "style": data.get("style", ""),
        "budget": data.get("budget"),
        "status": "active",
        "designs": [],
        "bookings": [],
    }
    project_id = insert_one(MongoCollection.PROJECTS, project)
    return api_response(data={"project_id": project_id, **project}, status_code=201)

@projects_bp.route("/projects/<project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id: str):
    """Get a project by ID."""
    project = find_by_id(MongoCollection.PROJECTS, project_id)
    if not project:
        return api_response(status="error", message="Project not found", status_code=404)
    return api_response(data=project)
