"""
Tests for GroqClient — Groq API interaction.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from app.llm.base_client import LLMResponse


class TestGroqClient:
    """Test GroqClient API interactions."""

    @patch("app.llm.groq_client.OpenAI")
    def test_init_creates_openai_client(self, mock_openai_class):
        """GroqClient creates an OpenAI client with Groq base URL."""
        from app.llm.groq_client import GroqClient

        client = GroqClient(
            api_key="test-key",
            api_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
        )

        mock_openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.groq.com/openai/v1",
            timeout=120,
        )

    @patch("app.llm.groq_client.OpenAI")
    def test_call_api_returns_llm_response(self, mock_openai_class):
        """_call_api returns a properly structured LLMResponse."""
        from app.llm.groq_client import GroqClient

        # Mock the OpenAI response
        mock_choice = MagicMock()
        mock_choice.message.content = "Test response content"
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance

        client = GroqClient(
            api_key="test-key",
            api_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
        )

        result = client._call_api(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.5,
            max_tokens=100,
        )

        assert isinstance(result, LLMResponse)
        assert result.content == "Test response content"
        assert result.model == "llama-3.3-70b-versatile"
        assert result.usage["total_tokens"] == 30
        assert result.finish_reason == "stop"

    @patch("app.llm.groq_client.OpenAI")
    def test_call_api_raises_on_error(self, mock_openai_class):
        """_call_api propagates API errors."""
        from app.llm.groq_client import GroqClient

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client_instance

        client = GroqClient(
            api_key="test-key",
            api_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
        )

        with pytest.raises(Exception, match="API Error"):
            client._call_api(
                messages=[{"role": "user", "content": "Hello"}],
            )

    @patch("app.llm.groq_client.OpenAI")
    def test_chat_method_builds_messages(self, mock_openai_class):
        """chat() builds the correct message list with system prompt + history."""
        from app.llm.groq_client import GroqClient

        mock_choice = MagicMock()
        mock_choice.message.content = "I can help with that!"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=10, total_tokens=15)

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance

        client = GroqClient(
            api_key="test-key",
            api_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
        )

        result = client.chat(
            user_message="Design my room",
            system_prompt="You are a designer",
            chat_history=[{"role": "user", "content": "Hi"}],
        )

        # Verify the API was called with correct messages
        call_args = mock_client_instance.chat.completions.create.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]

        # Should have: system + history + user message
        assert len(messages) >= 3
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Design my room"
        assert isinstance(result, LLMResponse)
