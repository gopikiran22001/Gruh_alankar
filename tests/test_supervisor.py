"""
Gruha Alankara — Supervisor Agent Tests
"""

from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from app.agents.schemas import AgentTask, TaskStatusEnum
from app.agents.supervisor_agent import SupervisorAgent


class TestSupervisorAgent:
    def setup_method(self):
        self.supervisor = SupervisorAgent()

    def test_create_fallback_plan_basic(self):
        """Test fallback plan creation for simple messages."""
        plan = self.supervisor._create_fallback_plan("Hello, I need help")
        assert plan.plan_id.startswith("fallback_")
        assert len(plan.tasks) >= 2  # At least memory + buddy
        assert plan.tasks[-1].agent_name == "memory_agent"  # memory store is last

    def test_create_fallback_plan_with_image(self):
        """Test fallback plan includes vision when image is provided."""
        plan = self.supervisor._create_fallback_plan("Analyze this room", has_image=True)
        agent_names = [t.agent_name for t in plan.tasks]
        assert "vision_agent" in agent_names

    def test_can_handle(self):
        assert self.supervisor.can_handle("plan")
        assert self.supervisor.can_handle("understand_intent")
        assert not self.supervisor.can_handle("unknown_task")

    def test_get_capability(self):
        cap = self.supervisor.get_capability()
        assert cap.agent_name == "supervisor_agent"
        assert len(cap.capabilities) > 0


class TestSupervisorPlanning:
    @pytest.mark.asyncio
    async def test_understand_intent(self):
        supervisor = SupervisorAgent()

        mock_response = MagicMock()
        mock_response.content = '{"primary_intent": "design_request", "entities": {"style": "scandinavian"}, "complexity": "moderate", "requires_agents": ["design_agent"], "confidence": 0.9}'
        mock_response.parse_json.return_value = {
            "primary_intent": "design_request",
            "entities": {"style": "scandinavian"},
            "complexity": "moderate",
            "requires_agents": ["design_agent"],
            "confidence": 0.9,
        }
        mock_response.reasoning_content = "User wants a design"
        mock_response.usage = {"total_tokens": 100}

        with patch.object(supervisor._llm, "reason", return_value=mock_response):
            task = AgentTask(
                task_id="test_intent",
                task_type="understand_intent",
                agent_name="supervisor_agent",
                parameters={"message": "I want a Scandinavian living room"},
            )

            result = await supervisor.execute(task)

            assert result.status == TaskStatusEnum.SUCCESS
            assert result.data["intent"]["primary_intent"] == "design_request"
