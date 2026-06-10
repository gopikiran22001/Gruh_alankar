"""Gruha Alankara — Voice API: POST /api/voice/transcribe, POST /api/voice/speak"""

from __future__ import annotations
import asyncio, uuid
from pathlib import Path
from flask import Blueprint, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.agents.schemas import AgentTask
from app.agents.registry import agent_registry
from app.api.middleware import api_response, rate_limit
from config.constants import AgentName
from config.settings import settings

voice_bp = Blueprint("voice", __name__)

@voice_bp.route("/transcribe", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def transcribe():
    """Transcribe audio to text."""
    user_id = get_jwt_identity()
    if "audio" not in request.files:
        return api_response(status="error", message="Audio file required", status_code=400)
    audio_file = request.files["audio"]
    upload_dir = Path(settings.storage.UPLOAD_DIR) / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(audio_file.filename).suffix or ".wav"
    audio_path = str(upload_dir / f"{uuid.uuid4().hex[:8]}{ext}")
    audio_file.save(audio_path)

    agent = agent_registry.get(AgentName.VOICE)
    if not agent:
        return api_response(status="error", message="Voice agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"stt_{uuid.uuid4().hex[:8]}",
        task_type="speech_to_text",
        agent_name=AgentName.VOICE,
        parameters={"audio_path": audio_path, "language": request.form.get("language")},
        metadata={"user_id": user_id},
    )
    result = asyncio.run(agent.run(task))
    return api_response(data=result.data)

@voice_bp.route("/speak", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def speak():
    """Convert text to speech."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    agent = agent_registry.get(AgentName.VOICE)
    if not agent:
        return api_response(status="error", message="Voice agent unavailable", status_code=503)
    task = AgentTask(
        task_id=f"tts_{uuid.uuid4().hex[:8]}",
        task_type="text_to_speech",
        agent_name=AgentName.VOICE,
        parameters={"text": data.get("text", ""), "language": data.get("language", "en")},
        metadata={"user_id": user_id},
    )
    result = asyncio.run(agent.run(task))
    if result.is_success and result.data.get("audio_path"):
        return send_file(result.data["audio_path"], mimetype="audio/wav")
    return api_response(data=result.data, status_code=400 if not result.is_success else 200)
