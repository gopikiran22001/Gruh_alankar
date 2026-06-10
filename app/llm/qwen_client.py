"""
Gruha Alankara — Qwen2.5-72B Instruct Client

Cloud API client for Qwen2.5-72B text model.
Used by: Buddy Agent, Design Agent, Furniture Agent, Budget Agent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.llm.base_client import BaseLLMClient, LLMResponse
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class QwenClient(BaseLLMClient):
    """
    Qwen2.5-72B Instruct API client using DashScope-compatible endpoint.

    Features:
    - OpenAI-compatible API format
    - Supports structured JSON output
    - Multi-language support (English, Hindi, Kannada, etc.)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
    ):
        api_key = api_key or settings.qwen.API_KEY
        api_url = api_url or settings.qwen.API_URL
        model = model or settings.qwen.MODEL

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
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call Qwen2.5-72B API."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            choice = response.choices[0]
            message = choice.message

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
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(
                "qwen_api_error",
                model=self.model,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        High-level chat method with conversation history support.

        Args:
            user_message: The user's current message.
            system_prompt: System instructions.
            chat_history: Previous messages for context.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens.

        Returns:
            LLMResponse with the model's reply.
        """
        messages: List[Dict[str, Any]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if chat_history:
            messages.extend(chat_history)

        messages.append({"role": "user", "content": user_message})

        return self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
