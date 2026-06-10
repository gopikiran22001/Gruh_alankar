"""
Gruha Alankara — Model Factory

Dynamic model provider abstraction that loads the correct LLM client
based on the MODEL_PROVIDER environment variable.

Supported providers:
- groq: Groq-hosted models (llama-3.3-70b-versatile, qwen/qwen3-32b)
- huggingface: HuggingFace Inference API or local models (Qwen2.5-7B-Instruct)

DeepSeek-R1 is NOT managed by this factory — it is always used directly
by the Supervisor and Critic agents.
"""

from __future__ import annotations

from typing import Optional

from app.llm.base_client import BaseLLMClient
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class ModelFactory:
    """
    Factory that creates the appropriate Groq LLM client based on configuration.

    Usage:
        client = ModelFactory.create_chat_client(model_name="llama-3.3-70b-versatile")
        response = client.chat(user_message="Hello", system_prompt="You are helpful.")

    The factory exclusively uses Groq. Different agents can request different 
    Groq models (e.g., llama-3.3-70b-versatile for complex reasoning, 
    llama-3.1-8b-instant for fast extraction). DeepSeek-R1 is NOT managed here.
    """

    _clients: dict[str, BaseLLMClient] = {}

    @classmethod
    def create_chat_client(cls, model_name: Optional[str] = None, force_new: bool = False) -> BaseLLMClient:
        """
        Create or return a cached chat LLM client for the specified Groq model.

        Args:
            model_name: The specific Groq model to use. Defaults to settings.groq.MODEL.
            force_new: If True, create a fresh client instance.

        Returns:
            A BaseLLMClient instance (GroqClient).
        """
        if model_name is None:
            model_name = settings.groq.MODEL or "llama-3.3-70b-versatile"

        if model_name in cls._clients and not force_new:
            return cls._clients[model_name]

        client = cls._create_groq_client(model_name)
        cls._clients[model_name] = client

        logger.info(
            "model_factory_client_created",
            provider="groq",
            model=client.model,
        )

        return client

    @classmethod
    def _create_groq_client(cls, model_name: str) -> BaseLLMClient:
        """Create a Groq-hosted LLM client."""
        from app.llm.groq_client import GroqClient

        return GroqClient(
            api_key=settings.groq.API_KEY,
            api_url=settings.groq.API_URL,
            model=model_name,
        )

    @classmethod
    def get_provider_name(cls) -> str:
        """Get the active model provider name (always groq)."""
        return "groq"

    @classmethod
    def get_model_name(cls) -> str:
        """Get the default active model name."""
        return settings.groq.MODEL or "llama-3.3-70b-versatile"

    @classmethod
    def reset(cls) -> None:
        """Reset the cached clients (useful for testing)."""
        cls._clients.clear()
        logger.info("model_factory_reset")

