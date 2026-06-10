"""Gruha Alankara — Budget Agent Tests."""

import pytest
from unittest.mock import patch, MagicMock
from app.agents.budget_agent import BudgetAgent
from app.agents.schemas import AgentTask, TaskStatusEnum


class TestBudgetAgent:
    def setup_method(self):
        self.agent = BudgetAgent()

    def test_can_handle(self):
        assert self.agent.can_handle("estimate_budget")
        assert self.agent.can_handle("generate_breakdown")
        assert self.agent.can_handle("optimize_budget")
        assert not self.agent.can_handle("unknown")

    @pytest.mark.asyncio
    async def test_estimate_budget(self):
        mock_response = MagicMock()
        mock_response.content = '{"estimated_total_inr": 45000, "within_budget": true}'
        mock_response.parse_json.return_value = {"estimated_total_inr": 45000, "within_budget": True}
        mock_response.usage = {"total_tokens": 50}

        with patch.object(self.agent._llm, "chat", return_value=mock_response):
            task = AgentTask(
                task_id="test_budget",
                task_type="estimate_budget",
                agent_name="budget_agent",
                parameters={},
                constraints={"budget": 50000},
            )
            result = await self.agent.execute(task)
            assert result.status == TaskStatusEnum.SUCCESS
            assert "budget" in result.data
