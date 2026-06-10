"""
Gruha Alankara — Abstract LLM Client Base

Provides a standard interface for all LLM clients with retry logic,
timeout handling, structured output parsing, and token tracking.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config.constants import MAX_LLM_RETRIES, LLM_TIMEOUT_SECONDS
from config.logging_config import get_logger

logger = get_logger(__name__)


class LLMResponse:
    """Standardized LLM response container."""

    def __init__(
        self,
        content: str,
        model: str,
        usage: Optional[Dict[str, int]] = None,
        reasoning_content: Optional[str] = None,
        finish_reason: Optional[str] = None,
        latency_ms: float = 0,
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.reasoning_content = reasoning_content
        self.finish_reason = finish_reason
        self.latency_ms = latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "reasoning_content": self.reasoning_content,
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
        }

    def parse_json(self) -> Dict[str, Any]:
        """
        Attempt to parse the response content as JSON.
        Handles markdown code blocks and raw JSON.
        """
        text = self.content.strip()

        # Strip markdown code block if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(
                "json_parse_failed",
                error=str(e),
                content_preview=text[:200],
            )
            raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e

    def parse_structured(self, model_class: Type[BaseModel]) -> BaseModel:
        """Parse the response into a Pydantic model."""
        data = self.parse_json()
        return model_class.model_validate(data)


class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM API clients.

    Subclasses implement _call_api() for their specific provider.
    This base handles retries, logging, and response wrapping.
    """

    def __init__(
        self,
        api_key: str,
        api_url: str,
        model: str,
        timeout: int = LLM_TIMEOUT_SECONDS,
        max_retries: int = MAX_LLM_RETRIES,
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._total_tokens_used = 0

    @abstractmethod
    def _call_api(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Make the actual API call. Implemented by each provider subclass.

        Args:
            messages: Chat messages in OpenAI-compatible format.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse with the model's output.
        """
        ...

    def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response from the LLM with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens in the response.
            system_prompt: Optional system prompt prepended to messages.

        Returns:
            LLMResponse with the model's output.
        """
        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        start_time = time.time()
        try:
            response = self._call_with_retry(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            response.latency_ms = (time.time() - start_time) * 1000

            # Track usage
            if response.usage:
                self._total_tokens_used += response.usage.get("total_tokens", 0)

            logger.info(
                "llm_generate_success",
                model=self.model,
                latency_ms=round(response.latency_ms, 1),
                tokens=response.usage.get("total_tokens", 0),
            )
            return response

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "llm_generate_failed",
                model=self.model,
                error=str(e),
                latency_ms=round(latency_ms, 1),
            )
            raise

    def generate_structured(
        self,
        messages: List[Dict[str, Any]],
        output_schema: Type[BaseModel],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseModel:
        """
        Generate and parse a structured (JSON) response.

        Appends a JSON format instruction to the system prompt and
        validates the output against the given Pydantic model.

        Args:
            messages: Chat messages.
            output_schema: Pydantic model class for output validation.
            temperature: Lower temperature for more deterministic JSON.
            max_tokens: Maximum tokens.
            system_prompt: Base system prompt.

        Returns:
            Parsed Pydantic model instance.
        """
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        json_instruction = (
            f"\n\nYou MUST respond with a valid JSON object that strictly "
            f"conforms to this schema:\n```json\n{schema_json}\n```\n"
            f"Do NOT include any text outside the JSON object."
        )

        full_system = (system_prompt or "") + json_instruction

        response = self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=full_system,
            **kwargs,
        )

        return response.parse_structured(output_schema)

    @retry(
        stop=stop_after_attempt(MAX_LLM_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    def _call_with_retry(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> LLMResponse:
        """Retry wrapper around _call_api."""
        return self._call_api(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    @property
    def total_tokens_used(self) -> int:
        """Total tokens consumed across all calls."""
        return self._total_tokens_used
