"""Gruha Alankara — Buddy Agent Tests."""

import pytest
from unittest.mock import patch, MagicMock
from app.agents.buddy_agent import BuddyAgent
from app.agents.schemas import AgentTask, TaskStatusEnum


class TestBuddyAgent:
    def setup_method(self):
        self.agent = BuddyAgent()

    @pytest.mark.asyncio
    async def test_chat(self):
        mock_response = MagicMock()
        mock_response.content = "Hello! Welcome to Gruha Alankara!"
        mock_response.usage = {"total_tokens": 30}

        with patch.object(self.agent._llm, "chat", return_value=mock_response):
            task = AgentTask(
                task_id="test_chat",
                task_type="chat",
                agent_name="buddy_agent",
                parameters={"message": "Hello"},
            )
            result = await self.agent.execute(task)
            assert result.status == TaskStatusEnum.SUCCESS
            assert "response" in result.data
            assert result.data["type"] == "chat"
