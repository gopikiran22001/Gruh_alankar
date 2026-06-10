"""
Gruha Alankara — MongoDB Data Access Layer

Provides typed collection accessors and common CRUD operations
for all MongoDB collections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

from app.extensions import get_db
from config.constants import MongoCollection
from config.logging_config import get_logger

logger = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Collection Accessors
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _col(name: str) -> Collection:
    """Get a MongoDB collection by name."""
    return get_db()[name]


def users_collection() -> Collection:
    return _col(MongoCollection.USERS)


def projects_collection() -> Collection:
    return _col(MongoCollection.PROJECTS)


def designs_collection() -> Collection:
    return _col(MongoCollection.DESIGNS)


def furniture_collection() -> Collection:
    return _col(MongoCollection.FURNITURE)


def bookings_collection() -> Collection:
    return _col(MongoCollection.BOOKINGS)


def chat_history_collection() -> Collection:
    return _col(MongoCollection.CHAT_HISTORY)


def agent_logs_collection() -> Collection:
    return _col(MongoCollection.AGENT_LOGS)


def voice_logs_collection() -> Collection:
    return _col(MongoCollection.VOICE_LOGS)


def trend_data_collection() -> Collection:
    return _col(MongoCollection.TREND_DATA)


def scraped_products_collection() -> Collection:
    return _col(MongoCollection.SCRAPED_PRODUCTS)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Generic CRUD Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def insert_one(collection_name: str, document: Dict[str, Any]) -> str:
    """
    Insert a single document with automatic timestamps.
    Returns the inserted document ID as string.
    """
    document["created_at"] = datetime.now(timezone.utc)
    document["updated_at"] = datetime.now(timezone.utc)
    result: InsertOneResult = _col(collection_name).insert_one(document)
    logger.debug("document_inserted", collection=collection_name, id=str(result.inserted_id))
    return str(result.inserted_id)


def find_one(collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find a single document matching the query."""
    doc = _col(collection_name).find_one(query)
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def find_by_id(collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
    """Find a document by its ObjectId."""
    try:
        doc = _col(collection_name).find_one({"_id": ObjectId(document_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except Exception:
        return None


def find_many(
    collection_name: str,
    query: Dict[str, Any],
    sort: Optional[List[tuple]] = None,
    limit: int = 100,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """Find multiple documents matching the query with pagination."""
    cursor = _col(collection_name).find(query).skip(skip).limit(limit)
    if sort:
        cursor = cursor.sort(sort)
    docs = []
    for doc in cursor:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs


def update_one(
    collection_name: str,
    query: Dict[str, Any],
    update: Dict[str, Any],
    upsert: bool = False,
) -> bool:
    """
    Update a single document. Automatically sets updated_at.
    Returns True if a document was modified.
    """
    if "$set" in update:
        update["$set"]["updated_at"] = datetime.now(timezone.utc)
    else:
        update["$set"] = {"updated_at": datetime.now(timezone.utc)}

    result: UpdateResult = _col(collection_name).update_one(query, update, upsert=upsert)
    return result.modified_count > 0 or result.upserted_id is not None


def update_by_id(
    collection_name: str,
    document_id: str,
    update: Dict[str, Any],
) -> bool:
    """Update a document by its ObjectId."""
    try:
        return update_one(collection_name, {"_id": ObjectId(document_id)}, update)
    except Exception:
        return False


def delete_one(collection_name: str, query: Dict[str, Any]) -> bool:
    """Delete a single document. Returns True if deleted."""
    result: DeleteResult = _col(collection_name).delete_one(query)
    return result.deleted_count > 0


def count_documents(collection_name: str, query: Dict[str, Any]) -> int:
    """Count documents matching the query."""
    return _col(collection_name).count_documents(query)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Chat History Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def save_chat_message(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Save a chat message to history."""
    message = {
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }
    return insert_one(MongoCollection.CHAT_HISTORY, message)


def get_chat_history(
    user_id: str,
    session_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Retrieve chat history for a user, optionally filtered by session."""
    query: Dict[str, Any] = {"user_id": user_id}
    if session_id:
        query["session_id"] = session_id
    return find_many(
        MongoCollection.CHAT_HISTORY,
        query,
        sort=[("created_at", -1)],
        limit=limit,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Log Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def log_agent_execution(
    workflow_id: str,
    agent_name: str,
    task_type: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    status: str,
    duration_ms: float,
    error: Optional[str] = None,
) -> str:
    """Log an agent execution for observability."""
    log_entry = {
        "workflow_id": workflow_id,
        "agent_name": agent_name,
        "task_type": task_type,
        "input_summary": _truncate_for_log(input_data),
        "output_summary": _truncate_for_log(output_data),
        "status": status,
        "duration_ms": duration_ms,
        "error": error,
    }
    return insert_one(MongoCollection.AGENT_LOGS, log_entry)


def _truncate_for_log(data: Any, max_length: int = 500) -> Any:
    """Truncate large data for log storage."""
    text = str(data)
    if len(text) > max_length:
        return text[:max_length] + "...[truncated]"
    return data
