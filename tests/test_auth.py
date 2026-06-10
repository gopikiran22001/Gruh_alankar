"""
Gruha Alankara — Auth API Tests
"""

from __future__ import annotations
from unittest.mock import patch


class TestAuthRegister:
    def test_register_success(self, client):
        with patch("app.api.auth.find_one") as mock_find, \
             patch("app.api.auth.insert_one") as mock_insert, \
             patch("app.api.auth.cache"):
            mock_find.return_value = None
            mock_insert.return_value = "new_user_id"

            response = client.post("/api/auth/register", json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "securepassword123",
                "full_name": "Test User",
            })

            assert response.status_code == 201
            data = response.get_json()
            assert data["status"] == "success"
            assert "access_token" in data["data"]
            assert "refresh_token" in data["data"]

    def test_register_missing_fields(self, client):
        response = client.post("/api/auth/register", json={
            "username": "ab",  # too short
            "email": "invalid",
            "password": "short",
        })
        assert response.status_code == 400

    def test_register_duplicate_email(self, client):
        with patch("app.api.auth.find_one") as mock_find, \
             patch("app.api.auth.cache"):
            mock_find.return_value = {"email": "test@example.com"}

            response = client.post("/api/auth/register", json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "securepassword123",
            })

            assert response.status_code == 409


class TestAuthLogin:
    def test_login_success(self, client):
        from app.auth.utils import hash_password
        hashed = hash_password("securepassword123")

        with patch("app.api.auth.find_one") as mock_find, \
             patch("app.api.auth.cache"):
            mock_find.return_value = {
                "_id": "user123",
                "username": "testuser",
                "email": "test@example.com",
                "password_hash": hashed,
                "is_active": True,
            }

            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "securepassword123",
            })

            assert response.status_code == 200
            data = response.get_json()
            assert "access_token" in data["data"]

    def test_login_wrong_password(self, client):
        from app.auth.utils import hash_password

        with patch("app.api.auth.find_one") as mock_find, \
             patch("app.api.auth.cache"):
            mock_find.return_value = {
                "_id": "user123",
                "username": "testuser",
                "email": "test@example.com",
                "password_hash": hash_password("correctpassword"),
                "is_active": True,
            }

            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword",
            })

            assert response.status_code == 401
