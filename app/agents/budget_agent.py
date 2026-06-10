"""
Gruha Alankara — Budget Agent

Calculates budgets, generates breakdowns, and optimizes costs
for interior design projects.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from config.constants import AgentName
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

BUDGET_SYSTEM_PROMPT = """You are an expert interior design budget consultant specializing in:
- Indian market pricing for furniture, decor, and materials
- Cost optimization strategies
- Category-wise budget allocation
- Tax (GST) calculations for furniture/home decor (12-18%)
- Delivery and installation cost estimation
- Phased purchasing strategies for tight budgets

Always provide realistic Indian Rupee (₹) pricing.
Respond with structured JSON."""


class BudgetAgent(BaseAgent):
    """
    Budget calculation and optimization agent.

    Handles:
    - Total cost estimation from design plans and product lists
    - Category-wise budget breakdown
    - Cost optimization and savings suggestions
    """

    name = AgentName.BUDGET
    description = "Calculates budgets, generates breakdowns, and optimizes costs for interior design projects"
    supported_task_types = [
        "estimate_budget",
        "generate_breakdown",
        "optimize_budget",
    ]
    estimated_latency_s = 10.0

    def __init__(self) -> None:
        super().__init__()
        from app.llm.groq_client import GroqClient
        self._llm = GroqClient(
            api_key=settings.groq_budget.API_KEY,
            api_url=settings.groq_budget.API_URL,
            model=settings.groq_budget.MODEL,
        )

    def _get_capabilities(self) -> List[str]:
        return [
            "Estimate total project budget from design plans",
            "Generate category-wise budget breakdowns",
            "Optimize budget with cost-saving alternatives",
            "Calculate GST and delivery costs",
            "Suggest phased purchasing strategies",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "estimate_budget": self._estimate_budget,
            "generate_breakdown": self._generate_breakdown,
            "optimize_budget": self._optimize_budget,
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

    async def _estimate_budget(self, task: AgentTask) -> AgentResult:
        """Estimate total project budget."""
        design_plan = task.context.get("design", {})
        product_list = task.context.get("products", [])
        recommendations = task.context.get("recommendations", {})
        user_budget = task.constraints.get("budget")

        prompt = f"""Estimate the total budget for this interior design project.

User's Budget Limit: {'₹' + str(user_budget) if user_budget else 'Not specified'}
Design Plan: {json.dumps(design_plan, indent=2) if design_plan else 'Not provided'}
Product List: {json.dumps(product_list[:15], indent=2) if product_list else 'Not provided'}
Recommendations: {json.dumps(recommendations, indent=2) if recommendations else 'Not provided'}

Respond with JSON:
{{
    "estimated_total_inr": 0,
    "subtotal_inr": 0,
    "gst_inr": 0,
    "delivery_inr": 0,
    "installation_inr": 0,
    "buffer_inr": 0,
    "within_budget": true/false,
    "budget_utilization_pct": 0.0,
    "items": [
        {{
            "name": "Item name",
            "category": "Category",
            "price_inr": 0,
            "quantity": 1
        }}
    ],
    "summary": "Brief budget summary"
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=BUDGET_SYSTEM_PROMPT,
            temperature=0.3,
        )

        try:
            budget_data = response.parse_json()
        except ValueError:
            budget_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"budget": budget_data},
            token_usage=response.usage,
        )

    async def _generate_breakdown(self, task: AgentTask) -> AgentResult:
        """Generate category-wise budget breakdown."""
        budget = task.parameters.get("budget", 0)
        categories = task.parameters.get(
            "categories",
            ["Furniture", "Decor", "Lighting", "Textiles", "Paint", "Accessories"],
        )

        prompt = f"""Generate a detailed category-wise budget breakdown for ₹{budget}.

Categories: {', '.join(categories)}

Respond with JSON:
{{
    "total_budget_inr": {budget},
    "breakdown": [
        {{
            "category": "Category name",
            "allocated_inr": 0,
            "percentage": 0.0,
            "items": ["Expected items"],
            "priority": "essential|important|nice_to_have"
        }}
    ],
    "allocation_strategy": "Brief explanation of allocation rationale",
    "tips": ["Budget tip 1", "Budget tip 2"]
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=BUDGET_SYSTEM_PROMPT,
            temperature=0.3,
        )

        try:
            breakdown_data = response.parse_json()
        except ValueError:
            breakdown_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"breakdown": breakdown_data},
            token_usage=response.usage,
        )

    async def _optimize_budget(self, task: AgentTask) -> AgentResult:
        """Optimize budget with cost-saving suggestions."""
        budget = task.parameters.get("budget", 0)
        target = task.parameters.get("target_budget", 0)
        products = task.parameters.get("products", [])

        prompt = f"""Optimize this interior design budget.

Current Budget: ₹{budget}
Target Budget: ₹{target}
Products/Items: {json.dumps(products[:15], indent=2) if products else 'None specified'}

Suggest ways to reduce costs. Respond with JSON:
{{
    "original_budget_inr": {budget},
    "optimized_budget_inr": 0,
    "savings_inr": 0,
    "savings_pct": 0.0,
    "optimizations": [
        {{
            "item": "Item name",
            "original_price_inr": 0,
            "suggested_price_inr": 0,
            "suggestion": "What to change",
            "alternative": "Alternative product/approach"
        }}
    ],
    "phased_plan": [
        {{
            "phase": "Phase 1: Essentials",
            "budget_inr": 0,
            "items": ["Item 1"]
        }}
    ],
    "diy_savings": ["DIY tip 1"]
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=BUDGET_SYSTEM_PROMPT,
            temperature=0.4,
        )

        try:
            optimize_data = response.parse_json()
        except ValueError:
            optimize_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"optimization": optimize_data},
            token_usage=response.usage,
        )
