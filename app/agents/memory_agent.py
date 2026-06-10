"""
Gruha Alankara — Memory Agent

Manages long-term user memory using ChromaDB vector store and BGE-M3 embeddings.
Stores preferences, conversation context, design history, and style preferences.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from app.database.vector_store import vector_store
from app.llm.embedding_client import embedding_client
from config.constants import AgentName, MemoryType, VectorCollection
from config.logging_config import get_logger

logger = get_logger(__name__)


class MemoryAgent(BaseAgent):
    """
    Long-term memory agent using ChromaDB + BGE-M3 embeddings.

    Responsibilities:
    - Store user preferences and interaction history
    - Retrieve relevant memories for context-aware responses
    - Update existing memories as preferences evolve
    - Semantic search across memory types
    """

    name = AgentName.MEMORY
    description = "Manages user long-term memory, preferences, design history, and style preferences"
    supported_task_types = [
        "store_memory",
        "retrieve_memory",
        "update_memory",
        "get_user_profile",
        "clear_memory",
    ]
    estimated_latency_s = 3.0

    def _get_capabilities(self) -> List[str]:
        return [
            "Store user preferences and conversation history",
            "Retrieve relevant memories via semantic search",
            "Update existing memory entries",
            "Build user profile from stored memories",
            "Manage design history and style preferences",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        """Route to the appropriate memory operation."""
        handlers = {
            "store_memory": self._store_memory,
            "retrieve_memory": self._retrieve_memory,
            "update_memory": self._update_memory,
            "get_user_profile": self._get_user_profile,
            "clear_memory": self._clear_memory,
        }

        handler = handlers.get(task.task_type)
        if not handler:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Unknown task type: {task.task_type}"],
            )

        return await handler(task)

    async def _store_memory(self, task: AgentTask) -> AgentResult:
        """Store a new memory entry."""
        user_id = task.parameters.get("user_id", "")
        content = task.parameters.get("content", "")
        memory_type = task.parameters.get("memory_type", MemoryType.CONVERSATION)
        metadata = task.parameters.get("metadata", {})

        if not content:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Content is required for storing memory"],
            )

        # Generate embedding
        embedding = embedding_client.embed_single(content)

        # Determine collection
        collection_name = self._get_collection_for_type(memory_type)

        # Generate unique ID
        memory_id = f"{user_id}_{uuid.uuid4().hex[:12]}"

        # Store with metadata
        doc_metadata = {
            "user_id": user_id,
            "memory_type": memory_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **metadata,
        }

        vector_store.add_documents(
            collection_name=collection_name,
            documents=[content],
            embeddings=[embedding],
            ids=[memory_id],
            metadatas=[doc_metadata],
        )

        logger.info(
            "memory_stored",
            user_id=user_id,
            memory_type=memory_type,
            memory_id=memory_id,
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "memory_id": memory_id,
                "memory_type": memory_type,
                "collection": collection_name,
            },
        )

    async def _retrieve_memory(self, task: AgentTask) -> AgentResult:
        """Retrieve relevant memories via semantic search."""
        user_id = task.parameters.get("user_id", "")
        query = task.parameters.get("query", "")
        memory_type = task.parameters.get("memory_type")
        top_k = task.parameters.get("top_k", 5)

        if not query:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Query is required for memory retrieval"],
            )

        # Generate query embedding
        query_embedding = embedding_client.embed_single(query)

        # Determine collection(s) to search
        if memory_type:
            collections = [self._get_collection_for_type(memory_type)]
        else:
            collections = [
                VectorCollection.USER_MEMORY,
                VectorCollection.CONVERSATION_MEMORY,
                VectorCollection.DESIGN_MEMORY,
                VectorCollection.STYLE_MEMORY,
            ]

        all_results = []
        for col_name in collections:
            try:
                results = vector_store.query(
                    collection_name=col_name,
                    query_embedding=query_embedding,
                    n_results=top_k,
                    where={"user_id": user_id} if user_id else None,
                )

                if results and results.get("ids") and results["ids"][0]:
                    for i, doc_id in enumerate(results["ids"][0]):
                        all_results.append({
                            "memory_id": doc_id,
                            "content": results["documents"][0][i] if results.get("documents") else "",
                            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                            "distance": results["distances"][0][i] if results.get("distances") else 0,
                            "collection": col_name,
                        })
            except Exception as e:
                logger.warning("memory_search_failed", collection=col_name, error=str(e))

        # Sort by distance (lower is more similar for cosine)
        all_results.sort(key=lambda x: x["distance"])
        all_results = all_results[:top_k]

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "memories": all_results,
                "total_found": len(all_results),
                "query": query,
            },
        )

    async def _update_memory(self, task: AgentTask) -> AgentResult:
        """Update an existing memory entry."""
        memory_id = task.parameters.get("memory_id", "")
        content = task.parameters.get("content", "")
        collection_name = task.parameters.get("collection", VectorCollection.USER_MEMORY)

        if not memory_id or not content:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["memory_id and content are required"],
            )

        # Generate new embedding
        embedding = embedding_client.embed_single(content)

        vector_store.update_document(
            collection_name=collection_name,
            doc_id=memory_id,
            document=content,
            embedding=embedding,
            metadata={"updated_at": datetime.now(timezone.utc).isoformat()},
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"memory_id": memory_id, "updated": True},
        )

    async def _get_user_profile(self, task: AgentTask) -> AgentResult:
        """Build a user profile from stored memories."""
        user_id = task.parameters.get("user_id", "")

        profile: Dict[str, Any] = {
            "user_id": user_id,
            "preferences": [],
            "style_preferences": [],
            "design_history": [],
            "recent_conversations": [],
        }

        # Fetch from each collection
        collections_map = {
            "preferences": VectorCollection.USER_MEMORY,
            "style_preferences": VectorCollection.STYLE_MEMORY,
            "design_history": VectorCollection.DESIGN_MEMORY,
            "recent_conversations": VectorCollection.CONVERSATION_MEMORY,
        }

        for key, col_name in collections_map.items():
            try:
                results = vector_store.get_documents(
                    collection_name=col_name,
                    where={"user_id": user_id},
                    limit=20,
                )
                if results and results.get("documents"):
                    profile[key] = [
                        {
                            "content": doc,
                            "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                        }
                        for i, doc in enumerate(results["documents"])
                    ]
            except Exception as e:
                logger.warning("profile_fetch_failed", collection=col_name, error=str(e))

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"profile": profile},
        )

    async def _clear_memory(self, task: AgentTask) -> AgentResult:
        """Clear all memories for a user."""
        user_id = task.parameters.get("user_id", "")
        memory_type = task.parameters.get("memory_type")

        if memory_type:
            collections = [self._get_collection_for_type(memory_type)]
        else:
            collections = [
                VectorCollection.USER_MEMORY,
                VectorCollection.CONVERSATION_MEMORY,
                VectorCollection.DESIGN_MEMORY,
                VectorCollection.STYLE_MEMORY,
            ]

        cleared_count = 0
        for col_name in collections:
            try:
                results = vector_store.get_documents(
                    collection_name=col_name,
                    where={"user_id": user_id},
                )
                if results and results.get("ids"):
                    vector_store.delete_documents(col_name, results["ids"])
                    cleared_count += len(results["ids"])
            except Exception as e:
                logger.warning("memory_clear_failed", collection=col_name, error=str(e))

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"cleared_count": cleared_count},
        )

    @staticmethod
    def _get_collection_for_type(memory_type: str) -> str:
        """Map memory type to ChromaDB collection name."""
        mapping = {
            MemoryType.PREFERENCE: VectorCollection.USER_MEMORY,
            MemoryType.CONVERSATION: VectorCollection.CONVERSATION_MEMORY,
            MemoryType.DESIGN_HISTORY: VectorCollection.DESIGN_MEMORY,
            MemoryType.STYLE_PREFERENCE: VectorCollection.STYLE_MEMORY,
        }
        return mapping.get(memory_type, VectorCollection.USER_MEMORY)
