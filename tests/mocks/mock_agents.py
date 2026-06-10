"""Gruha Alankara — Mock Agent Results."""

from __future__ import annotations
from app.agents.schemas import AgentResult, TaskStatusEnum


def mock_vision_result(task_id: str = "mock_vision") -> AgentResult:
    return AgentResult(
        task_id=task_id,
        agent_name="vision_agent",
        status=TaskStatusEnum.SUCCESS,
        data={
            "room_description": {"caption": "A modern living room with natural lighting"},
            "detected_objects": {"objects": [{"label": "sofa", "confidence": 0.95}]},
            "color_analysis": {"dominant_colors": [{"hex": "#e8d5b7", "percentage": 35}]},
            "lighting_analysis": {"classification": "well_lit", "brightness": 150},
        },
        confidence_score=0.9,
    )


def mock_design_result(task_id: str = "mock_design") -> AgentResult:
    return AgentResult(
        task_id=task_id,
        agent_name="design_agent",
        status=TaskStatusEnum.SUCCESS,
        data={
            "design": {
                "design_title": "Scandinavian Serenity",
                "style_description": "Clean lines with warm wood tones",
                "estimated_total_inr": 45000,
            }
        },
        confidence_score=0.85,
    )


def mock_budget_result(task_id: str = "mock_budget") -> AgentResult:
    return AgentResult(
        task_id=task_id,
        agent_name="budget_agent",
        status=TaskStatusEnum.SUCCESS,
        data={
            "budget": {
                "estimated_total_inr": 48500,
                "within_budget": True,
                "budget_utilization_pct": 97,
            }
        },
    )
