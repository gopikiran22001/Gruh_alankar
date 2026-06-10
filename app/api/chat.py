"""
Gruha Alankara — Chat API Endpoint

POST /api/chat — Main entry point for the autonomous agent system.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.middleware import api_response, rate_limit
from app.orchestration.executor import workflow_executor
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=30, window=60)
def chat():
    """
    Main chat endpoint — the primary interface to the autonomous agent system.

    Accepts:
    - text message (required)
    - image file (optional)
    - audio file (optional)
    - budget, style, room_type constraints (optional)

    The Supervisor Agent autonomously plans and executes the workflow.
    """
    user_id = get_jwt_identity()

    # Extract message
    message = request.form.get("message") or ""
    if request.is_json:
        data = request.get_json()
        message = data.get("message", "")
        budget = data.get("budget")
        style = data.get("style")
        room_type = data.get("room_type")
        session_id = data.get("session_id", str(uuid.uuid4())[:8])
        project_id = data.get("project_id")
        chat_history = data.get("chat_history", [])
    else:
        budget = request.form.get("budget", type=float)
        style = request.form.get("style")
        room_type = request.form.get("room_type")
        session_id = request.form.get("session_id", str(uuid.uuid4())[:8])
        project_id = request.form.get("project_id")
        chat_history = []

    if not message:
        return api_response(
            status="error",
            message="Message is required",
            status_code=400,
        )

    # Handle file uploads
    image_paths = []
    audio_path = None

    if "image" in request.files:
        image_file = request.files["image"]
        if image_file.filename:
            upload_dir = Path(settings.storage.UPLOAD_DIR) / user_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            ext = Path(image_file.filename).suffix or ".jpg"
            image_filename = f"{uuid.uuid4().hex[:8]}{ext}"
            image_path = str(upload_dir / image_filename)
            image_file.save(image_path)
            image_paths.append(image_path)

    if "audio" in request.files:
        audio_file = request.files["audio"]
        if audio_file.filename:
            upload_dir = Path(settings.storage.UPLOAD_DIR) / user_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            ext = Path(audio_file.filename).suffix or ".wav"
            audio_filename = f"{uuid.uuid4().hex[:8]}{ext}"
            audio_path = str(upload_dir / audio_filename)
            audio_file.save(audio_path)

    # Run the autonomous workflow
    try:
        result = asyncio.run(
            workflow_executor.run_workflow(
                user_id=user_id,
                session_id=session_id,
                message=message,
                image_paths=image_paths if image_paths else None,
                audio_path=audio_path,
                chat_history=chat_history,
                budget=budget,
                style=style,
                room_type=room_type,
                project_id=project_id,
            )
        )

        return api_response(
            data={
                "response": result.get("response", ""),
                "workflow_id": result.get("workflow_id", ""),
                "execution_summary": result.get("metadata", {}),
            },
            metadata={
                "agents_used": list(result.get("agent_results", {}).keys()),
                "status": result.get("status", "success"),
            },
        )

    except Exception as e:
        logger.error("chat_endpoint_error", error=str(e), user_id=user_id)
        return api_response(
            status="error",
            message="An error occurred processing your request. Please try again.",
            status_code=500,
        )
