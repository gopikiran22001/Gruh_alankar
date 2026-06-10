"""Gruha Alankara — Vision Agent Tests."""

import pytest
from unittest.mock import patch, AsyncMock
from app.agents.vision_agent import VisionAgent
from app.agents.schemas import AgentTask, TaskStatusEnum


class TestVisionAgent:
    def setup_method(self):
        self.agent = VisionAgent()

    def test_validate_image_missing(self):
        assert not self.agent._validate_image("")
        assert not self.agent._validate_image("/nonexistent/path.jpg")

    @pytest.mark.asyncio
    async def test_extract_colors_missing_image(self):
        task = AgentTask(
            task_id="test_colors",
            task_type="extract_colors",
            agent_name="vision_agent",
            parameters={"image_path": "/missing.jpg"},
        )
        result = await self.agent.execute(task)
        assert result.status == TaskStatusEnum.FAILED

    def test_lighting_recommendation(self):
        rec = self.agent._lighting_recommendation("dark")
        assert "ambient" in rec.lower() or "lighting" in rec.lower()
