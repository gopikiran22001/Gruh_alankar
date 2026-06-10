"""
Gruha Alankara — Chat API Tests
"""

from __future__ import annotations
from unittest.mock import patch, AsyncMock


class TestChatEndpoint:
    def test_chat_requires_auth(self, client):
        response = client.post("/api/chat", json={"message": "hello"})
        assert response.status_code == 401

    def test_chat_requires_message(self, client, auth_headers):
        response = client.post("/api/chat", json={}, headers=auth_headers)
        assert response.status_code == 400

    def test_chat_success(self, client, auth_headers):
        mock_result = {
            "workflow_id": "wf_test123",
            "response": "Hello! How can I help with your interior design?",
            "status": "success",
            "agent_results": {},
            "metadata": {"duration_ms": 100},
        }

        with patch("app.api.chat.workflow_executor") as mock_executor:
            mock_executor.run_workflow = AsyncMock(return_value=mock_result)

            response = client.post("/api/chat", json={
                "message": "I need help designing my living room",
                "style": "scandinavian",
                "budget": 50000,
            }, headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "success"
            assert "response" in data["data"]
