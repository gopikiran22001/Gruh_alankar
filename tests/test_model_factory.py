"""
Tests for ModelFactory — Groq-based LLM client creation.
"""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from app.llm.model_factory import ModelFactory


class TestModelFactory:
    """Test ModelFactory creates Groq clients correctly."""

    def teardown_method(self):
        ModelFactory.reset()

    @patch("app.llm.groq_client.GroqClient")
    def test_creates_groq_client_with_default_model(self, mock_groq_class):
        """ModelFactory creates a GroqClient with default model."""
        mock_instance = MagicMock()
        mock_instance.model = "llama-3.3-70b-versatile"
        mock_groq_class.return_value = mock_instance

        ModelFactory.reset()
        client = ModelFactory.create_chat_client()

        assert client == mock_instance
        mock_groq_class.assert_called_once()

    @patch("app.llm.groq_client.GroqClient")
    def test_creates_groq_client_with_specific_model(self, mock_groq_class):
        """ModelFactory creates a GroqClient with specified model."""
        mock_instance = MagicMock()
        mock_instance.model = "llama-3.1-8b-instant"
        mock_groq_class.return_value = mock_instance

        ModelFactory.reset()
        client = ModelFactory.create_chat_client(model_name="llama-3.1-8b-instant")

        assert client == mock_instance
        mock_groq_class.assert_called_once()

    @patch("app.llm.groq_client.GroqClient")
    def test_caches_client_by_model(self, mock_groq_class):
        """Second call with same model returns cached instance."""
        mock_instance = MagicMock()
        mock_groq_class.return_value = mock_instance

        ModelFactory.reset()
        client1 = ModelFactory.create_chat_client(model_name="llama-3.3-70b-versatile")
        client2 = ModelFactory.create_chat_client(model_name="llama-3.3-70b-versatile")

        assert client1 is client2
        assert mock_groq_class.call_count == 1  # Only created once

    @patch("app.llm.groq_client.GroqClient")
    def test_different_models_create_different_clients(self, mock_groq_class):
        """Different models create different client instances."""
        def side_effect(*args, **kwargs):
            mock = MagicMock()
            mock.model = kwargs.get('model', 'default')
            return mock
            
        mock_groq_class.side_effect = side_effect

        ModelFactory.reset()
        client1 = ModelFactory.create_chat_client(model_name="llama-3.3-70b-versatile")
        client2 = ModelFactory.create_chat_client(model_name="llama-3.1-8b-instant")

        assert client1 is not client2
        assert mock_groq_class.call_count == 2

    @patch("app.llm.groq_client.GroqClient")
    def test_force_new_creates_fresh_instance(self, mock_groq_class):
        """force_new=True bypasses the cache."""
        mock_groq_class.return_value = MagicMock()

        ModelFactory.reset()
        ModelFactory.create_chat_client(model_name="test-model")
        ModelFactory.create_chat_client(model_name="test-model", force_new=True)

        assert mock_groq_class.call_count == 2

    def test_reset_clears_cache(self):
        """reset() clears the cached clients."""
        ModelFactory._clients["test"] = MagicMock()
        ModelFactory.reset()
        assert len(ModelFactory._clients) == 0

    def test_get_model_name(self):
        """get_model_name returns the default Groq model."""
        name = ModelFactory.get_model_name()
        # Should return a valid model name (from settings or default)
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_provider_name(self):
        """get_provider_name returns 'groq'."""
        assert ModelFactory.get_provider_name() == "groq"
