"""Gruha Alankara — Mock LLM Clients."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.llm.base_client import BaseLLMClient, LLMResponse


class MockLLMClient(BaseLLMClient):
    """Mock LLM client that returns configurable responses."""

    def __init__(self, default_response: str = "Mock response"):
        super().__init__(api_key="mock", api_url="http://mock", model="mock-model")
        self.default_response = default_response
        self.call_count = 0
        self.last_messages: List[Dict[str, Any]] = []

    def _call_api(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        self.call_count += 1
        self.last_messages = messages
        return LLMResponse(
            content=self.default_response,
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )


class MockDeepSeekClient(MockLLMClient):
    """Mock DeepSeek client with reasoning content."""

    def _call_api(self, messages, temperature=0.0, max_tokens=8192, **kwargs):
        self.call_count += 1
        self.last_messages = messages
        return LLMResponse(
            content=self.default_response,
            model="mock-deepseek",
            usage={"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60},
            reasoning_content="Mock reasoning chain",
        )
