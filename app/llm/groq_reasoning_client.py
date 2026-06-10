"""
Gruha Alankara — Groq Reasoning Client

Cloud API client for Groq's reasoning-capable models (llama-3.3-70b-versatile).
Used by: Supervisor Agent, Critic Agent.

Note: While Groq models don't have a dedicated reasoning_content field like DeepSeek-R1,
llama-3.3-70b-versatile can still perform chain-of-thought reasoning within its responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.llm.base_client import BaseLLMClient, LLMResponse
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class GroqReasoningClient(BaseLLMClient):
    """
    Groq Reasoning API client using OpenAI-compatible endpoint.

    Special handling:
    - Extracts `reasoning_content` from the response (chain-of-thought)
    - Supports higher timeouts for reasoning-heavy tasks
    - Temperature fixed at 0 for reasoning models
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 180,
    ):
        api_key = api_key or settings.groq_reasoning.API_KEY
        api_url = api_url or settings.groq_reasoning.API_URL
        model = model or settings.groq_reasoning.MODEL

        super().__init__(
            api_key=api_key,
            api_url=api_url,
            model=model,
            timeout=timeout,
        )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
            timeout=self.timeout,
        )

    def _call_api(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 8192,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Call Groq Reasoning API.

        Note: Reasoning models recommend temperature=0 for reasoning tasks.
        The model's reasoning process is returned in reasoning_content.
        """
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                stream=False,
            )

            choice = response.choices[0]
            message = choice.message

            # Extract reasoning content (reasoning model specific)
            reasoning_content = None
            if hasattr(message, "reasoning_content"):
                reasoning_content = message.reasoning_content

            # Build usage dict
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=message.content or "",
                model=self.model,
                usage=usage,
                reasoning_content=reasoning_content,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(
                "groq_reasoning_api_error",
                model=self.model,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def reason(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """
        High-level method for reasoning tasks.
        Optimized for the Supervisor and Critic agents.

        Args:
            prompt: The reasoning prompt.
            context: Optional context to include.
            max_tokens: Maximum tokens for the response.

        Returns:
            LLMResponse with both content and reasoning_content.
        """
        messages: List[Dict[str, Any]] = []

        if context:
            messages.append({
                "role": "system",
                "content": context,
            })

        messages.append({
            "role": "user",
            "content": prompt,
        })

        return self.generate(
            messages=messages,
            temperature=0.0,  # Deterministic for reasoning
            max_tokens=max_tokens,
        )
