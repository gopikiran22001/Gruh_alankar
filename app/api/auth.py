"""
Gruha Alankara — Auth API Endpoints

POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from app.api.middleware import api_response, rate_limit
from app.auth.utils import hash_password, verify_password, validate_email
from app.database.mongo import find_one, insert_one
from app.database.redis_cache import cache
from config.constants import MongoCollection
from config.logging_config import get_logger

logger = get_logger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
@rate_limit(max_requests=10, window=3600)
def register():
    """Register a new user."""
    data = request.get_json()
    if not data:
        return api_response(status="error", message="JSON body required", status_code=400)

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    # Validation
    errors = []
    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters")
    if not email or not validate_email(email):
        errors.append("Valid email is required")
    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters")

    if errors:
        return api_response(status="error", message="; ".join(errors), status_code=400)

    # Check existing user
    if find_one(MongoCollection.USERS, {"email": email}):
        return api_response(status="error", message="Email already registered", status_code=409)

    if find_one(MongoCollection.USERS, {"username": username}):
        return api_response(status="error", message="Username already taken", status_code=409)

    # Create user
    user_doc = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "full_name": full_name,
        "preferences": {},
        "is_active": True,
    }

    user_id = insert_one(MongoCollection.USERS, user_doc)

    # Generate tokens
    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)

    logger.info("user_registered", user_id=user_id, username=username)

    return api_response(
        data={
            "user_id": user_id,
            "username": username,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        message="Registration successful",
        status_code=201,
    )


@auth_bp.route("/login", methods=["POST"])
@rate_limit(max_requests=20, window=300)
def login():
    """Authenticate user and return tokens."""
    data = request.get_json()
    if not data:
        return api_response(status="error", message="JSON body required", status_code=400)

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return api_response(status="error", message="Email and password required", status_code=400)

    # Find user
    user = find_one(MongoCollection.USERS, {"email": email})
    if not user:
        return api_response(status="error", message="Invalid credentials", status_code=401)

    if not user.get("is_active", True):
        return api_response(status="error", message="Account is disabled", status_code=403)

    # Verify password
    if not verify_password(password, user["password_hash"]):
        return api_response(status="error", message="Invalid credentials", status_code=401)

    user_id = user["_id"]
    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)

    logger.info("user_logged_in", user_id=user_id)

    return api_response(
        data={
            "user_id": user_id,
            "username": user["username"],
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        message="Login successful",
    )


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)

    return api_response(data={"access_token": access_token})


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Logout user by blocklisting their current token."""
    jti = get_jwt()["jti"]
    cache.blocklist_token(jti, ttl=3600)

    logger.info("user_logged_out", user_id=get_jwt_identity())

    return api_response(message="Logged out successfully")


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Get the current user's profile."""
    user_id = get_jwt_identity()
    user = find_one(MongoCollection.USERS, {"_id": user_id})

    if not user:
        return api_response(status="error", message="User not found", status_code=404)

    return api_response(
        data={
            "user_id": user_id,
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "full_name": user.get("full_name", ""),
            "preferences": user.get("preferences", {}),
            "is_active": user.get("is_active", True),
        }
    )
