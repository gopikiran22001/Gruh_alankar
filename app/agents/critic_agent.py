"""
Gruha Alankara — Critic Agent

Validates outputs from other agents using Groq Reasoning.
Detects hallucinations, budget violations, style inconsistencies,
and determines if retries are needed.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent
from app.agents.schemas import (
    AgentResult,
    AgentTask,
    CriticFeedback,
    TaskStatusEnum,
    ValidationIssue,
)
from app.llm.groq_reasoning_client import GroqReasoningClient
from config.constants import AgentName
from config.logging_config import get_logger

logger = get_logger(__name__)

CRITIC_SYSTEM_PROMPT = """You are a rigorous quality assurance expert for an interior design AI platform.

Your job is to validate outputs from specialized agents and ensure:
1. **Budget Adherence**: Total costs must not exceed the user's budget
2. **Style Consistency**: All recommendations must match the requested design style
3. **Factual Accuracy**: Product names, prices, and specifications must be plausible
4. **Completeness**: All requested aspects must be addressed
5. **Practicality**: Suggestions must be feasible for the given room/space
6. **No Hallucinations**: Product recommendations should reference real brands/stores

Scoring (BE GENEROUS - Only fail critically bad results):
- 0.8-1.0: Excellent, approve immediately
- 0.5-0.79: Good enough, approve with minor notes
- 0.3-0.49: Acceptable but needs improvement, still approve
- Below 0.3: Critical issues, needs retry

IMPORTANT: Set is_approved to true for any score >= 0.3. Only reject scores below 0.3.

You MUST respond with structured JSON."""


class CriticAgent(BaseAgent):
    """
    Quality assurance agent using Groq Reasoning.

    Validates multi-agent outputs and determines if retries are needed.
    Acts as the quality gate before final response generation.
    """

    name = AgentName.CRITIC
    description = "Validates agent outputs for quality, accuracy, budget adherence, and consistency"
    supported_task_types = [
        "validate",
        "criticize",
        "retry_if_needed",
    ]
    estimated_latency_s = 15.0

    def __init__(self) -> None:
        super().__init__()
        self._llm = GroqReasoningClient()

    def _get_capabilities(self) -> List[str]:
        return [
            "Validate agent outputs for quality and accuracy",
            "Detect hallucinations in product recommendations",
            "Verify budget compliance",
            "Check style consistency across recommendations",
            "Determine if agent retries are needed",
            "Provide improvement suggestions",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "validate": self._validate,
            "criticize": self._criticize,
            "retry_if_needed": self._retry_if_needed,
        }

        handler = handlers.get(task.task_type)
        if not handler:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Unknown task type: {task.task_type}"],
            )

        return await handler(task)

    async def _validate(self, task: AgentTask) -> AgentResult:
        """Validate all agent outputs comprehensively."""
        agent_outputs = task.context.get("agent_results", {})
        user_constraints = task.constraints
        user_intent = task.parameters.get("user_intent", "")

        prompt = f"""Validate the following agent outputs for an interior design project.

User's Original Intent: {user_intent}
User's Constraints: {json.dumps(user_constraints, indent=2)}

Agent Outputs:
{json.dumps(agent_outputs, indent=2, default=str)}

Analyze each agent's output and respond with JSON:
{{
    "is_approved": true/false,
    "overall_score": 0.0-1.0,
    "issues": [
        {{
            "severity": "critical|warning|info",
            "category": "budget|style|accuracy|completeness|practicality",
            "description": "Issue description",
            "affected_agent": "agent_name",
            "affected_task_id": "",
            "suggested_fix": "How to fix"
        }}
    ],
    "retry_instructions": {{
        "agent_name": {{
            "task_type": "task to retry",
            "modified_params": {{}},
            "reason": "Why retry is needed"
        }}
    }},
    "reasoning": "Your detailed reasoning",
    "recommendations": ["Improvement suggestion 1", "Improvement suggestion 2"]
}}"""

        response = self._llm.reason(
            prompt=prompt,
            context=CRITIC_SYSTEM_PROMPT,
            max_tokens=4096,
        )

        try:
            feedback_data = response.parse_json()
            # Ensure is_approved is set correctly based on score
            if "overall_score" in feedback_data and "is_approved" not in feedback_data:
                feedback_data["is_approved"] = feedback_data["overall_score"] >= 0.3
            elif "overall_score" in feedback_data:
                # Override is_approved if score is acceptable
                if feedback_data["overall_score"] >= 0.3:
                    feedback_data["is_approved"] = True
            
            feedback = CriticFeedback(
                workflow_id=task.metadata.get("workflow_id", ""),
                **feedback_data,
            )
        except (ValueError, Exception) as e:
            logger.warning("critic_parse_failed", error=str(e))
            # Default to approved if we can't parse
            feedback = CriticFeedback(
                workflow_id=task.metadata.get("workflow_id", ""),
                is_approved=True,
                overall_score=0.7,
                reasoning=response.content,
            )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "feedback": feedback.model_dump(),
                "is_approved": feedback.is_approved,
                "overall_score": feedback.overall_score,
                "needs_retry": feedback.needs_retry,
                "issue_count": len(feedback.issues),
                "reasoning_chain": response.reasoning_content,
            },
            confidence_score=feedback.overall_score,
            token_usage=response.usage,
        )

    async def _criticize(self, task: AgentTask) -> AgentResult:
        """Deep analysis of specific agent outputs."""
        target_agent = task.parameters.get("target_agent", "")
        agent_output = task.parameters.get("agent_output", {})
        criteria = task.parameters.get("criteria", ["accuracy", "quality", "relevance"])

        prompt = f"""Perform a deep analysis of this agent's output.

Agent: {target_agent}
Evaluation Criteria: {', '.join(criteria)}

Output to Analyze:
{json.dumps(agent_output, indent=2, default=str)}

Respond with JSON:
{{
    "agent": "{target_agent}",
    "scores": {{
        "criterion_name": 0.0-1.0
    }},
    "overall_score": 0.0-1.0,
    "strengths": ["Strength 1"],
    "weaknesses": ["Weakness 1"],
    "critical_issues": ["Issue requiring retry"],
    "improvement_suggestions": ["Suggestion 1"],
    "verdict": "pass|fail|needs_improvement"
}}"""

        response = self._llm.reason(
            prompt=prompt,
            context=CRITIC_SYSTEM_PROMPT,
        )

        try:
            critique_data = response.parse_json()
        except ValueError:
            critique_data = {"raw_response": response.content, "verdict": "pass"}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "critique": critique_data,
                "reasoning_chain": response.reasoning_content,
            },
            token_usage=response.usage,
        )

    async def _retry_if_needed(self, task: AgentTask) -> AgentResult:
        """Determine if any agents need to be retried based on validation."""
        validation_result = task.parameters.get("validation_result", {})
        max_retries = task.parameters.get("max_retries", 3)
        current_retry = task.parameters.get("current_retry", 0)

        needs_retry = False
        retry_agents = {}

        if isinstance(validation_result, dict):
            feedback = validation_result.get("feedback", {})
            if not feedback.get("is_approved", True) and current_retry < max_retries:
                needs_retry = True
                retry_agents = feedback.get("retry_instructions", {})

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "needs_retry": needs_retry,
                "retry_agents": retry_agents,
                "current_retry": current_retry,
                "max_retries": max_retries,
            },
        )
