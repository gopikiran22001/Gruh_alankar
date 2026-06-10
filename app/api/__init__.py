"""
Gruha Alankara — API Blueprint Registration
"""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all API blueprints with the Flask app."""
    from app.api.auth import auth_bp
    from app.api.chat import chat_bp
    from app.api.vision import vision_bp
    from app.api.design import design_bp
    from app.api.furniture import furniture_bp
    from app.api.budget import budget_bp
    from app.api.booking import booking_bp
    from app.api.web import web_bp
    from app.api.voice import voice_bp
    from app.api.projects import projects_bp
    from app.api.design_studio import design_studio_bp
    from app.api.uploads import uploads_bp

    blueprints = [
        (auth_bp, "/api/auth"),
        (chat_bp, "/api"),
        (vision_bp, "/api/vision"),
        (design_bp, "/api/design"),
        (furniture_bp, "/api/furniture"),
        (budget_bp, "/api/budget"),
        (booking_bp, "/api/booking"),
        (web_bp, "/api/web"),
        (voice_bp, "/api/voice"),
        (projects_bp, "/api"),
        (design_studio_bp, "/api/design-studio"),
        (uploads_bp, "/api/uploads"),
    ]

    for blueprint, prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=prefix)
