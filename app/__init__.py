"""
Gruha Alankara — Flask Application Factory

Creates and configures the Flask application with all extensions,
blueprints, error handlers, and middleware.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

from config.logging_config import setup_logging, get_logger
from config.settings import settings

logger = get_logger(__name__)


def create_app(testing: bool = False) -> Flask:
    """
    Application factory pattern.

    Args:
        testing: If True, uses test configuration overrides.

    Returns:
        Configured Flask application instance.
    """
    # Disable ChromaDB telemetry FIRST before any imports
    import os
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    
    # Initialize logging first
    setup_logging()

    app = Flask(__name__)

    # ── Core Config ──
    app.config["SECRET_KEY"] = settings.flask.SECRET_KEY
    app.config["DEBUG"] = settings.flask.FLASK_DEBUG
    app.config["TESTING"] = testing

    # ── JWT Config ──
    app.config["JWT_SECRET_KEY"] = settings.jwt.SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        seconds=settings.jwt.ACCESS_TOKEN_EXPIRES
    )
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
        seconds=settings.jwt.REFRESH_TOKEN_EXPIRES
    )
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"

    # ── Upload Config ──
    app.config["MAX_CONTENT_LENGTH"] = settings.storage.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    upload_dir = Path(settings.storage.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_DIR"] = str(upload_dir)

    # ── CORS ──
    # Allow requests from the Vite dev server and any configured frontend origin.
    # CORS_ORIGINS env var allows overriding in production (comma-separated list).
    raw_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
    )

    # ── Initialize Extensions ──
    _init_extensions(app)

    # ── Register Blueprints ──
    _register_blueprints(app)

    # ── Register Error Handlers ──
    _register_error_handlers(app)

    # ── Register Health Check ──
    _register_health_check(app)

    logger.info(
        "application_initialized",
        env=settings.flask.FLASK_ENV,
        debug=settings.flask.FLASK_DEBUG,
    )

    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    from app.extensions import jwt, init_mongo, init_redis

    # JWT
    jwt.init_app(app)

    # Setup JWT callbacks
    from app.auth.jwt_handlers import setup_jwt_callbacks
    setup_jwt_callbacks(jwt, app)

    # MongoDB (lazy connection)
    init_mongo(app)

    # Redis
    init_redis(app)

    # ChromaDB Vector Store
    from app.database.vector_store import vector_store
    try:
        vector_store.connect()
        logger.info("vector_store_connected")
    except Exception as e:
        logger.warning("vector_store_connection_failed", error=str(e))

    # Initialize all agents
    from app.agents.registry import initialize_agents
    try:
        initialize_agents()
        logger.info("agents_initialized")
    except Exception as e:
        logger.error("agents_initialization_failed", error=str(e))

    # Preload models (embedding + voice)
    try:
        from preload_models import preload_all_models
        preload_all_models()
    except Exception as e:
        logger.warning("model_preload_failed", error=str(e))

    logger.info("extensions_initialized")

    # Print startup banner
    from app.observability.startup_banner import print_startup_banner
    print_startup_banner(
        host=settings.server.HOST,
        port=settings.server.PORT,
        debug=settings.flask.FLASK_DEBUG
    )


def _register_blueprints(app: Flask) -> None:
    """Register all API blueprints."""
    from app.api import register_blueprints
    register_blueprints(app)
    logger.info("blueprints_registered")


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "status": "error",
            "error": "bad_request",
            "message": str(error.description) if hasattr(error, "description") else "Bad request",
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "status": "error",
            "error": "unauthorized",
            "message": "Authentication required",
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "status": "error",
            "error": "forbidden",
            "message": "Access forbidden",
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "error": "not_found",
            "message": "Resource not found",
        }), 404

    @app.errorhandler(413)
    def payload_too_large(error):
        return jsonify({
            "status": "error",
            "error": "payload_too_large",
            "message": f"File exceeds maximum size of {settings.storage.MAX_UPLOAD_SIZE_MB}MB",
        }), 413

    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "message": str(error.description) if hasattr(error, "description") else "Validation error",
        }), 422

    @app.errorhandler(429)
    def rate_limited(error):
        return jsonify({
            "status": "error",
            "error": "rate_limited",
            "message": "Too many requests. Please slow down.",
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("internal_server_error", error=str(error))
        return jsonify({
            "status": "error",
            "error": "internal_error",
            "message": "An internal error occurred. Please try again later.",
        }), 500


def _register_health_check(app: Flask) -> None:
    """Register the /api/health endpoint."""

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Docker/load balancer probes."""
        health = {"status": "healthy", "service": "gruha-alankara"}

        # Check MongoDB
        try:
            from app.extensions import mongo_client
            if mongo_client:
                mongo_client.admin.command("ping")
                health["mongodb"] = "connected"
            else:
                health["mongodb"] = "not_initialized"
        except Exception as e:
            health["mongodb"] = f"error: {str(e)}"
            health["status"] = "degraded"

        # Check Redis
        try:
            from app.extensions import redis_client
            if redis_client:
                redis_client.ping()
                health["redis"] = "connected"
            else:
                health["redis"] = "not_initialized"
        except Exception as e:
            health["redis"] = f"error: {str(e)}"
            health["status"] = "degraded"

        # Check ChromaDB
        try:
            from app.database.vector_store import vector_store
            if vector_store._client:
                vector_store.client.heartbeat()
                health["chromadb"] = "connected"
            else:
                health["chromadb"] = "not_initialized"
        except Exception as e:
            health["chromadb"] = f"error: {str(e)}"
            health["status"] = "degraded"

        status_code = 200 if health["status"] == "healthy" else 503
        return jsonify(health), status_code
