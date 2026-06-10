"""
Gruha Alankara — File Serving API

Serves uploaded images, generated renders, and other files.
"""

from flask import Blueprint, send_file, abort
from pathlib import Path
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)

uploads_bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")


@uploads_bp.route("/<user_id>/<filename>", methods=["GET"])
def serve_file(user_id: str, filename: str):
    """
    Serve uploaded or generated image files.
    
    URL: /api/uploads/{user_id}/{filename}
    Example: /api/uploads/user123/room_abc123.jpg
    """
    try:
        file_path = Path(settings.storage.UPLOAD_DIR) / user_id / filename
        
        if not file_path.exists():
            logger.warning("file_not_found", path=str(file_path))
            abort(404)
        
        if not file_path.is_file():
            logger.warning("not_a_file", path=str(file_path))
            abort(404)
        
        # Determine mimetype
        ext = file_path.suffix.lower()
        mimetypes = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        
        mimetype = mimetypes.get(ext, "application/octet-stream")
        
        # Convert to string for send_file
        return send_file(str(file_path), mimetype=mimetype)
        
    except Exception as e:
        logger.error("file_serving_error", error=str(e), user_id=user_id, filename=filename)
        abort(500)
