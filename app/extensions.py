"""
Gruha Alankara — Flask Extension Singletons

Centralized initialization of JWT, MongoDB, Redis, and Celery.
These are imported throughout the app to access shared instances.
"""

from __future__ import annotations

from typing import Optional

import redis
from flask import Flask
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from pymongo.database import Database

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JWT Manager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
jwt = JWTManager()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MongoDB
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
mongo_client: Optional[MongoClient] = None
mongo_db: Optional[Database] = None


def init_mongo(app: Flask) -> None:
    """Initialize MongoDB connection."""
    global mongo_client, mongo_db
    try:
        mongo_client = MongoClient(
            settings.mongo.URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=5,
        )
        mongo_db = mongo_client[settings.mongo.DB_NAME]

        # Verify connection
        mongo_client.admin.command("ping")
        logger.info("mongodb_connected", db=settings.mongo.DB_NAME)

        # Create indexes
        _ensure_indexes(mongo_db)
    except Exception as e:
        logger.error("mongodb_connection_failed", error=str(e))
        # Don't crash the app — allow degraded mode
        mongo_client = None
        mongo_db = None


def _ensure_indexes(db: Database) -> None:
    """Create necessary MongoDB indexes for performance."""
    try:
        # Users
        db.users.create_index("email", unique=True)
        db.users.create_index("username", unique=True)

        # Projects
        db.projects.create_index("user_id")
        db.projects.create_index([("user_id", 1), ("created_at", -1)])

        # Chat history
        db.chat_history.create_index([("user_id", 1), ("created_at", -1)])
        db.chat_history.create_index("session_id")

        # Agent logs
        db.agent_logs.create_index([("agent_name", 1), ("created_at", -1)])
        db.agent_logs.create_index("workflow_id")
        db.agent_logs.create_index([("created_at", -1)])

        # Bookings
        db.bookings.create_index("user_id")
        db.bookings.create_index("status")

        # Scraped products
        db.scraped_products.create_index("source")
        db.scraped_products.create_index("category")
        db.scraped_products.create_index([("scraped_at", -1)])

        # Designs
        db.designs.create_index("project_id")
        db.designs.create_index("user_id")

        # Furniture
        db.furniture.create_index("category")
        db.furniture.create_index("style")

        logger.info("mongodb_indexes_created")
    except Exception as e:
        logger.warning("mongodb_index_creation_failed", error=str(e))


def get_db() -> Database:
    """Get the MongoDB database instance. Raises if not connected."""
    if mongo_db is None:
        raise RuntimeError("MongoDB is not connected. Check MONGODB_URI configuration.")
    return mongo_db


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Redis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
redis_client: Optional[redis.Redis] = None


def init_redis(app: Flask) -> None:
    """Initialize Redis connection."""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.redis.URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            max_connections=20,
        )
        redis_client.ping()
        logger.info("redis_connected", url=settings.redis.URL)
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        redis_client = None


def get_redis() -> redis.Redis:
    """Get the Redis client instance. Raises if not connected."""
    if redis_client is None:
        raise RuntimeError("Redis is not connected. Check REDIS_URL configuration.")
    return redis_client
