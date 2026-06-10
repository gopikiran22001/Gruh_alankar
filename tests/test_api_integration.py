"""
Tests for API Integration — Auth flow, Chat flow, and Booking flow.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock, AsyncMock

import pytest


class TestAuthIntegration:
    """Test full auth lifecycle: register → login → profile → logout."""

    @patch("app.database.mongo.find_one")
    @patch("app.database.mongo.insert_one")
    def test_register_returns_tokens(self, mock_insert, mock_find, client):
        """POST /api/auth/register returns access + refresh tokens."""
        mock_find.return_value = None  # No existing user
        mock_insert.return_value = "new_user_id"

        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "strongpassword123",
        })

        assert response.status_code in (200, 201)
        data = response.get_json()
        assert "access_token" in data.get("data", {})
        assert "refresh_token" in data.get("data", {})

    @patch("app.database.mongo.find_one")
    def test_login_with_valid_credentials(self, mock_find, client):
        """POST /api/auth/login succeeds with correct password."""
        from werkzeug.security import generate_password_hash

        mock_find.return_value = {
            "_id": "user_123",
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": generate_password_hash("correct_password"),
            "is_active": True,
        }

        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "correct_password",
        })

        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data.get("data", {})

    def test_login_with_invalid_credentials(self, client):
        """POST /api/auth/login fails with wrong password."""
        with patch("app.database.mongo.find_one") as mock_find:
            mock_find.return_value = None

            response = client.post("/api/auth/login", json={
                "email": "wrong@example.com",
                "password": "wrongpassword",
            })

            assert response.status_code in (401, 404)

    @patch("app.database.mongo.find_one")
    def test_get_profile_with_valid_token(self, mock_find, client, auth_headers):
        """GET /api/auth/profile returns user data when authenticated."""
        mock_find.return_value = {
            "_id": "test_user_id",
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
        }

        response = client.get("/api/auth/profile", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data.get("data", {}).get("email") == "test@example.com"

    def test_get_profile_without_token(self, client):
        """GET /api/auth/profile returns 401 without auth."""
        response = client.get("/api/auth/profile")
        assert response.status_code in (401, 422)


class TestChatIntegration:
    """Test chat endpoint integration."""

    def test_chat_requires_auth(self, client):
        """POST /api/chat returns 401 without auth token."""
        response = client.post("/api/chat", json={"message": "Hello"})
        assert response.status_code in (401, 422)

    @patch("app.agents.registry.agent_registry")
    def test_chat_with_valid_message(self, mock_registry, client, auth_headers):
        """POST /api/chat processes a message and returns a response."""
        # Mock the supervisor agent
        mock_supervisor = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"response": "Here is your design recommendation."}
        mock_result.status = "success"
        mock_supervisor.run = AsyncMock(return_value=mock_result)
        mock_registry.get.return_value = mock_supervisor

        response = client.post("/api/chat", json={
            "message": "Design my living room in modern style",
            "session_id": "test-session",
        }, headers=auth_headers)

        # Should succeed or be processed
        assert response.status_code in (200, 201, 202)


class TestBookingIntegration:
    """Test booking endpoints."""

    def test_booking_list_requires_auth(self, client):
        """GET /api/booking/list returns 401 without auth."""
        response = client.get("/api/booking/list")
        assert response.status_code in (401, 422)

    @patch("app.agents.registry.agent_registry")
    def test_booking_list_with_auth(self, mock_registry, client, auth_headers):
        """GET /api/booking/list returns bookings for authenticated user."""
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"bookings": [], "total_count": 0}
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_registry.get.return_value = mock_agent

        response = client.get("/api/booking/list", headers=auth_headers)
        assert response.status_code == 200
