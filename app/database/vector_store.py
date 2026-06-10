"""
Gruha Alankara — ChromaDB Vector Store Manager

Manages vector collections for user memory, conversation history,
design memory, and style memory using BGE-M3 embeddings.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# Disable ChromaDB telemetry BEFORE importing chromadb
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.api import ClientAPI

from config.constants import VectorCollection
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class VectorStoreManager:
    """
    Manages ChromaDB collections for semantic memory.

    Supports:
    - Embedding storage and retrieval
    - Semantic search with metadata filtering
    - Collection lifecycle management
    """

    _instance: Optional["VectorStoreManager"] = None

    def __new__(cls) -> "VectorStoreManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._client: Optional[ClientAPI] = None
        self._collections: Dict[str, chromadb.Collection] = {}

    def connect(self) -> None:
        """Establish connection to ChromaDB server (cloud or local)."""
        try:
            if settings.chromadb.use_cloud_client:
                # Use cloud client (ChromaDB Cloud)
                self._client = chromadb.CloudClient(
                    api_key=settings.chromadb.API_KEY,
                    tenant=settings.chromadb.TENANT,
                    database=settings.chromadb.DATABASE,
                )
                logger.info(
                    "chromadb_cloud_connected",
                    tenant=settings.chromadb.TENANT,
                    database=settings.chromadb.DATABASE,
                )
            else:
                # Use local persistent client
                persist_dir = settings.chromadb.PERSIST_DIR
                os.makedirs(persist_dir, exist_ok=True)
                
                # Create settings with telemetry disabled
                chroma_settings = chromadb.config.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
                
                self._client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=chroma_settings
                )
                logger.info(
                    "chromadb_local_connected",
                    path=persist_dir,
                )
            
            # Verify connection
            self._client.heartbeat()
            # Initialize collections
            self._init_collections()
        except Exception as e:
            logger.error("chromadb_connection_failed", error=repr(e))
            self._client = None

    def _init_collections(self) -> None:
        """Create or get all required collections."""
        if not self._client:
            return

        collection_names = [
            VectorCollection.USER_MEMORY,
            VectorCollection.CONVERSATION_MEMORY,
            VectorCollection.DESIGN_MEMORY,
            VectorCollection.STYLE_MEMORY,
        ]

        for name in collection_names:
            try:
                self._collections[name] = self._client.get_or_create_collection(name=name)
                logger.info("collection_initialized", collection=name, count=self._collections[name].count())
            except Exception as e:
                logger.error("collection_init_failed", collection=name, error=repr(e))

    @property
    def client(self) -> ClientAPI:
        if self._client is None:
            raise RuntimeError("ChromaDB is not connected. Call connect() first.")
        return self._client

    def get_collection(self, name: str) -> chromadb.Collection:
        """Get a named collection."""
        if name not in self._collections:
            raise ValueError(f"Collection {name} not initialized")
        return self._collections[name]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Core Operations
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Add documents with pre-computed embeddings to a collection.

        Args:
            collection_name: Target collection name.
            documents: Raw text documents.
            embeddings: Pre-computed embedding vectors.
            ids: Unique document IDs.
            metadatas: Optional metadata for each document.
        """
        collection = self.get_collection(collection_name)
        collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        logger.debug(
            "documents_added",
            collection=collection_name,
            count=len(documents),
        )

    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Query a collection with a pre-computed embedding.

        Args:
            collection_name: Collection to query.
            query_embedding: Query vector.
            n_results: Number of results to return.
            where: Metadata filter conditions.
            include: Fields to include (documents, metadatas, distances).

        Returns:
            ChromaDB query results dict.
        """
        collection = self.get_collection(collection_name)
        include = include or ["documents", "metadatas", "distances"]

        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": include,
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)
        logger.debug(
            "vector_query",
            collection=collection_name,
            n_results=n_results,
            matches=len(results.get("ids", [[]])[0]),
        )
        return results

    def update_document(
        self,
        collection_name: str,
        doc_id: str,
        document: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update an existing document in a collection."""
        collection = self.get_collection(collection_name)
        kwargs: Dict[str, Any] = {"ids": [doc_id]}
        if document:
            kwargs["documents"] = [document]
        if embedding:
            kwargs["embeddings"] = [embedding]
        if metadata:
            kwargs["metadatas"] = [metadata]
        collection.update(**kwargs)

    def delete_documents(
        self,
        collection_name: str,
        ids: List[str],
    ) -> None:
        """Delete documents from a collection by IDs."""
        collection = self.get_collection(collection_name)
        collection.delete(ids=ids)
        logger.debug(
            "documents_deleted",
            collection=collection_name,
            count=len(ids),
        )

    def get_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get documents by IDs or metadata filter."""
        collection = self.get_collection(collection_name)
        kwargs: Dict[str, Any] = {
            "include": ["documents", "metadatas"],
            "limit": limit,
        }
        if ids:
            kwargs["ids"] = ids
        if where:
            kwargs["where"] = where
        return collection.get(**kwargs)

    def collection_count(self, collection_name: str) -> int:
        """Get the number of documents in a collection."""
        collection = self.get_collection(collection_name)
        return collection.count()


# Module-level singleton
vector_store = VectorStoreManager()
