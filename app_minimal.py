#!/usr/bin/env python3
"""
Minimal Flask app test without complex dependencies.
Tests core functionality: MongoDB, Redis, ChromaDB, JWT.
"""

import os
import sys

# Disable ChromaDB telemetry FIRST before any other imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"

sys.path.append('.')

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config.logging_config import setup_logging, get_logger
from config.settings import settings

logger = get_logger(__name__)

def create_minimal_app() -> Flask:
    """Create minimal Flask app for testing core functionality."""
    setup_logging()
    
    app = Flask(__name__)
    
    # Basic config
    app.config["SECRET_KEY"] = settings.flask.SECRET_KEY
    app.config["JWT_SECRET_KEY"] = settings.jwt.SECRET_KEY
    
    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # JWT
    jwt = JWTManager(app)
    
    # Initialize core extensions
    try:
        from app.extensions import init_mongo, init_redis
        init_mongo(app)
        init_redis(app)
        logger.info("core_extensions_initialized")
    except Exception as e:
        logger.warning("extension_init_failed", error=str(e))
    
    # Initialize vector store
    try:
        from app.database.vector_store import vector_store
        vector_store.connect()
        logger.info("vector_store_connected")
    except Exception as e:
        logger.warning("vector_store_connection_failed", error=str(e))
    
    # Basic routes
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        health = {"status": "healthy", "service": "gruha-alankara-minimal"}
        
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
    
    @app.route("/api/config", methods=["GET"])
    def config_info():
        """Configuration info endpoint."""
        return jsonify({
            "chromadb_mode": "cloud" if settings.chromadb.use_cloud_client else "local",
            "mongodb_db": settings.mongo.DB_NAME,
            "environment": settings.flask.FLASK_ENV,
        })
    
    logger.info("minimal_app_created", debug=settings.flask.FLASK_DEBUG)
    return app

if __name__ == "__main__":
    app = create_minimal_app()
    print("🚀 Starting minimal Flask application...")
    print(f"Health check: http://localhost:{settings.server.PORT}/api/health")
    print(f"Config info: http://localhost:{settings.server.PORT}/api/config")
    
    app.run(
        host=settings.server.HOST,
        port=settings.server.PORT,
        debug=settings.flask.FLASK_DEBUG,
    )