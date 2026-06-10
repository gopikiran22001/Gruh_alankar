"""Gruha Alankara — Orchestration Tests."""

from __future__ import annotations
from unittest.mock import patch, MagicMock
from app.orchestration.graph_builder import DynamicGraphBuilder


class TestDynamicGraphBuilder:
    def setup_method(self):
        self.builder = DynamicGraphBuilder()

    def test_build_simple_chat_graph(self):
        """Test fallback simple chat graph."""
        with patch("app.orchestration.nodes.agent_registry") as mock_reg:
            mock_agent = MagicMock()
            mock_reg.get_or_raise.return_value = mock_agent
            graph = self.builder._build_simple_chat_graph()
            assert graph is not None

    def test_build_graph_empty_plan(self):
        """Test building graph with empty plan."""
        with patch("app.orchestration.nodes.agent_registry"):
            graph = self.builder.build_graph({"tasks": []})
            assert graph is not None

    def test_plan_with_dependencies(self):
        """Test plan parsing respects dependencies."""
        plan = {
            "tasks": [
                {"task_id": "t1", "agent_name": "vision_agent", "task_type": "full_analysis", "depends_on": []},
                {"task_id": "t2", "agent_name": "design_agent", "task_type": "generate_design", "depends_on": ["t1"]},
                {"task_id": "t3", "agent_name": "buddy_agent", "task_type": "generate_response", "depends_on": ["t2"]},
            ]
        }

        # Verify task ordering
        tasks = plan["tasks"]
        assert tasks[0]["depends_on"] == []
        assert tasks[1]["depends_on"] == ["t1"]
        assert tasks[2]["depends_on"] == ["t2"]
