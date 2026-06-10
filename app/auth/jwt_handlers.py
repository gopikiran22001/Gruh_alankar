"""Gruha Alankara — JWT Callback Handlers."""

from __future__ import annotations
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from app.database.redis_cache import cache
from config.logging_config import get_logger

logger = get_logger(__name__)


def setup_jwt_callbacks(jwt: JWTManager, app: Flask) -> None:
    """Register JWT callback handlers."""

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return cache.is_token_blocklisted(jti)

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Token has been revoked"}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"status": "error", "message": "Invalid token"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"status": "error", "message": "Authorization required"}), 401
