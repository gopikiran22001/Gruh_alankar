"""Gruha Alankara — Auth Decorators."""

from __future__ import annotations
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.database.mongo import find_by_id
from config.constants import MongoCollection


def require_auth(f):
    """Decorator that requires a valid JWT and active user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = find_by_id(MongoCollection.USERS, user_id)
        if not user or not user.get("is_active", True):
            return jsonify({"status": "error", "message": "Account not found or disabled"}), 403
        return f(*args, **kwargs)
    return decorated
