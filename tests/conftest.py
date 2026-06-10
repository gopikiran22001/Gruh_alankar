"""
Gruha Alankara — Pytest Fixtures

Shared fixtures for Flask test client, mock DB, mock LLM, etc.
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch

# Set test environment before importing app
os.environ["FLASK_ENV"] = "testing"
os.environ["FLASK_DEBUG"] = "0"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["MONGODB_DB_NAME"] = "gruha_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DEEPSEEK_API_KEY"] = "test-key"
os.environ["QWEN_API_KEY"] = "test-key"
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["MODEL_PROVIDER"] = "groq"


@pytest.fixture
def app():
    """Create a test Flask application."""
    with patch("app.extensions.init_mongo"), \
         patch("app.extensions.init_redis"):
        from app import create_app
        app = create_app(testing=True)
        app.config["TESTING"] = True
        yield app


@pytest.fixture
def client(app):
    """Create a test HTTP client."""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Get auth headers with a valid JWT for testing."""
    with patch("app.database.mongo.find_one") as mock_find, \
         patch("app.database.mongo.insert_one") as mock_insert:
        mock_insert.return_value = "test_user_id"
        mock_find.return_value = None  # No existing user

        # Register
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
        })

        if response.status_code == 201:
            data = response.get_json()
            token = data["data"]["access_token"]
            return {"Authorization": f"Bearer {token}"}

    # Fallback: create token directly
    from flask_jwt_extended import create_access_token
    with client.application.app_context():
        token = create_access_token(identity="test_user_id")
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_llm_response():
    """Mock LLM response factory."""
    from app.llm.base_client import LLMResponse

    def _create(content: str = "test response", **kwargs):
        return LLMResponse(
            content=content,
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            **kwargs,
        )

    return _create


@pytest.fixture
def mock_agent_result():
    """Mock AgentResult factory."""
    from app.agents.schemas import AgentResult, TaskStatusEnum

    def _create(
        task_id: str = "test_task",
        agent_name: str = "test_agent",
        status: TaskStatusEnum = TaskStatusEnum.SUCCESS,
        data: dict = None,
    ):
        return AgentResult(
            task_id=task_id,
            agent_name=agent_name,
            status=status,
            data=data or {"result": "test"},
        )

    return _create


@pytest.fixture
def mock_groq_client():
    """Mock GroqClient for testing."""
    mock = MagicMock()
    mock.model = "llama-3.3-70b-versatile"
    mock.api_url = "https://api.groq.com/openai/v1"
    return mock


@pytest.fixture
def mock_model_factory(mock_groq_client):
    """Mock ModelFactory that returns a mock GroqClient."""
    with patch("app.llm.model_factory.ModelFactory.create_chat_client") as mock_factory:
        mock_factory.return_value = mock_groq_client
        yield mock_factory
