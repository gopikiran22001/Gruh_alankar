"""
Gruha Alankara — BGE-M3 Embedding Client

Generates text embeddings using the BAAI/bge-m3 model.
Supports both local (sentence-transformers) and API-based embedding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class EmbeddingClient:
    """
    Embedding generation client for BGE-M3.

    Modes:
    - Local: Uses sentence-transformers (requires GPU/CPU)
    - API: Uses an external embedding API endpoint

    The client lazily loads the model on first use.
    """

    _instance: Optional["EmbeddingClient"] = None

    def __new__(cls) -> "EmbeddingClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._model = None
        self._api_url = settings.embedding.API_URL
        self._model_name = settings.embedding.MODEL
        self._dimension: Optional[int] = None

    def _load_model(self) -> None:
        """Lazily load the sentence-transformer model."""
        if self._model is not None:
            return

        if self._api_url:
            logger.info("embedding_using_api", url=self._api_url)
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("embedding_loading_model", model=self._model_name)
            self._model = SentenceTransformer(self._model_name)
            # Get embedding dimension
            test_embedding = self._model.encode(["test"])
            self._dimension = test_embedding.shape[1]
            logger.info(
                "embedding_model_loaded",
                model=self._model_name,
                dimension=self._dimension,
            )
        except Exception as e:
            logger.error("embedding_model_load_failed", error=str(e))
            raise

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        self._load_model()

        if self._api_url:
            return self._embed_via_api(texts)

        return self._embed_local(texts)

    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        results = self.embed([text])
        return results[0]

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model."""
        try:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error("local_embedding_failed", error=str(e), count=len(texts))
            raise

    def _embed_via_api(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using external API."""
        import httpx

        try:
            response = httpx.post(
                self._api_url,
                json={
                    "model": self._model_name,
                    "input": texts,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            # OpenAI-compatible response format
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
        except Exception as e:
            logger.error("api_embedding_failed", error=str(e), count=len(texts))
            raise

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is None:
            self._load_model()
            if self._dimension is None:
                # Default BGE-M3 dimension
                return 1024
        return self._dimension

    def cosine_similarity(
        self,
        embedding_a: List[float],
        embedding_b: List[float],
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        a = np.array(embedding_a)
        b = np.array(embedding_b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Module-level singleton
embedding_client = EmbeddingClient()
