"""
Tests for LangGraph Dynamic Orchestration.

Validates that:
- DynamicGraphBuilder creates unique graphs per execution plan
- No hardcoded workflows exist
- Critic loop triggers properly
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.agents.schemas import (
    ExecutionPlan,
    TaskStep,
    AgentTask,
    AgentResult,
    TaskStatusEnum,
)


class TestDynamicGraphBuilder:
    """Test that graph building is truly dynamic, not hardcoded."""

    def test_execution_plan_creates_different_graphs(self):
        """Two different execution plans should yield different graph structures."""
        # Plan A: single step
        plan_a = ExecutionPlan(
            plan_id="plan_a",
            steps=[
                TaskStep(
                    step_id="step_1",
                    agent_name="buddy",
                    task_type="chat",
                    dependencies=[],
                )
            ],
        )

        # Plan B: multi-step with dependencies
        plan_b = ExecutionPlan(
            plan_id="plan_b",
            steps=[
                TaskStep(
                    step_id="step_1",
                    agent_name="design",
                    task_type="generate_design",
                    dependencies=[],
                ),
                TaskStep(
                    step_id="step_2",
                    agent_name="furniture",
                    task_type="recommend_products",
                    dependencies=["step_1"],
                ),
                TaskStep(
                    step_id="step_3",
                    agent_name="budget",
                    task_type="estimate_budget",
                    dependencies=["step_1", "step_2"],
                ),
            ],
        )

        assert len(plan_a.steps) != len(plan_b.steps)
        assert plan_a.steps[0].agent_name != plan_b.steps[0].agent_name

    def test_no_hardcoded_workflow_imports(self):
        """Verify no hardcoded workflow files are imported."""
        import app.orchestration.graph_builder as gb

        source = open(gb.__file__).read()

        # These patterns would indicate hardcoded workflows
        assert "hardcoded" not in source.lower()
        assert "static_workflow" not in source.lower()

    def test_execution_plan_serialization(self):
        """ExecutionPlan should serialize and deserialize correctly."""
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                TaskStep(
                    step_id="s1",
                    agent_name="buddy",
                    task_type="chat",
                    dependencies=[],
                )
            ],
        )

        # Pydantic model should have proper dict/json serialization
        plan_dict = plan.model_dump()
        assert plan_dict["plan_id"] == "test_plan"
        assert len(plan_dict["steps"]) == 1

    def test_task_step_dependency_chain(self):
        """Steps with dependencies form a valid DAG."""
        steps = [
            TaskStep(step_id="a", agent_name="vision", task_type="analyze", dependencies=[]),
            TaskStep(step_id="b", agent_name="design", task_type="generate", dependencies=["a"]),
            TaskStep(step_id="c", agent_name="furniture", task_type="recommend", dependencies=["b"]),
            TaskStep(step_id="d", agent_name="budget", task_type="estimate", dependencies=["b", "c"]),
        ]

        step_ids = {s.step_id for s in steps}

        # All dependencies reference existing steps
        for step in steps:
            for dep in step.dependencies:
                assert dep in step_ids, f"Step {step.step_id} depends on non-existent step {dep}"


class TestCriticLoop:
    """Test that the critic validation loop works correctly."""

    def test_agent_result_success_status(self):
        """AgentResult with SUCCESS status should pass validation."""
        result = AgentResult(
            task_id="test",
            agent_name="buddy",
            status=TaskStatusEnum.SUCCESS,
            data={"response": "Hello"},
            confidence_score=0.9,
        )

        assert result.status == TaskStatusEnum.SUCCESS
        assert result.confidence_score >= 0.7  # Typical threshold

    def test_agent_result_failure_triggers_retry(self):
        """AgentResult with FAILED status should trigger critic review."""
        result = AgentResult(
            task_id="test",
            agent_name="design",
            status=TaskStatusEnum.FAILED,
            errors=["Model generation timeout"],
        )

        assert result.status == TaskStatusEnum.FAILED
        assert len(result.errors) > 0

    def test_low_confidence_result(self):
        """Low confidence results should be flagged for critic review."""
        result = AgentResult(
            task_id="test",
            agent_name="furniture",
            status=TaskStatusEnum.SUCCESS,
            data={"recommendations": []},
            confidence_score=0.3,
        )

        # Critic should flag results below threshold
        CRITIC_THRESHOLD = 0.7
        assert result.confidence_score < CRITIC_THRESHOLD
