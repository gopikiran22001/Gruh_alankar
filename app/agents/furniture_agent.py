"""
Gruha Alankara — Furniture Agent

AI-powered product recommendation, ranking, and comparison
using Groq Llama-3.1-8b combined with web-scraped product data.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from config.constants import AgentName
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

FURNITURE_SYSTEM_PROMPT = """You are an expert furniture consultant specializing in:
- Indian furniture market (Pepperfry, Urban Ladder, IKEA, Amazon India)
- Interior design styles and furniture matching
- Price-to-quality assessment
- Space optimization with furniture selection
- Budget-conscious recommendations

When ranking or recommending products, consider:
1. Style match with the design theme
2. Price-to-value ratio
3. Material quality and durability
4. Space compatibility
5. Customer ratings and reviews
6. Delivery and return policies

Always respond with structured JSON."""


class FurnitureAgent(BaseAgent):
    """
    Furniture recommendation agent powered by Groq Llama-3.1-8b.

    Combines AI reasoning with scraped product data to provide
    intelligent furniture recommendations, rankings, and comparisons.
    """

    name = AgentName.FURNITURE
    description = "Recommends, ranks, and compares furniture products based on design, budget, and style"
    supported_task_types = [
        "recommend_products",
        "rank_products",
        "compare_products",
    ]
    estimated_latency_s = 15.0

    def __init__(self) -> None:
        super().__init__()
        from app.llm.groq_client import GroqClient
        self._llm = GroqClient(
            api_key=settings.groq_furniture.API_KEY,
            api_url=settings.groq_furniture.API_URL,
            model=settings.groq_furniture.MODEL,
        )

    def _get_capabilities(self) -> List[str]:
        return [
            "AI-powered furniture recommendations matching design style",
            "Multi-criteria product ranking (price, quality, style match)",
            "Side-by-side product comparison",
            "Budget-optimized product selection",
            "Style-specific furniture matching",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "recommend_products": self._recommend_products,
            "rank_products": self._rank_products,
            "compare_products": self._compare_products,
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

    async def _recommend_products(self, task: AgentTask) -> AgentResult:
        """Generate AI-powered product recommendations."""
        design = task.context.get("design", {})
        budget = task.constraints.get("budget")
        style = task.parameters.get("style", "modern")
        room_type = task.parameters.get("room_type", "living room")
        scraped_products = task.context.get("products", [])

        prompt = f"""Based on the following design and context, recommend the best furniture products.

Design Style: {style}
Room Type: {room_type}
Budget: {'₹' + str(budget) if budget else 'Not specified'}
Design Details: {json.dumps(design, indent=2) if design else 'General design'}
Available Products from Web Search: {json.dumps(scraped_products[:20], indent=2) if scraped_products else 'None scraped yet'}

Recommend furniture items. Respond with JSON:
{{
    "recommendations": [
        {{
            "category": "Seating|Tables|Storage|Lighting|Decor",
            "item_name": "Specific product name",
            "description": "Why this item works",
            "estimated_price_inr": 0,
            "style_match_score": 0.0-1.0,
            "priority": "must_have|recommended|optional",
            "alternatives": ["Alt 1", "Alt 2"],
            "where_to_buy": ["Store names"],
            "matched_product": null
        }}
    ],
    "total_estimated_inr": 0,
    "budget_status": "within_budget|over_budget|under_budget",
    "savings_tips": ["Tip 1"]
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=FURNITURE_SYSTEM_PROMPT,
            temperature=0.5,
        )

        try:
            rec_data = response.parse_json()
        except ValueError:
            rec_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"recommendations": rec_data},
            token_usage=response.usage,
        )

    async def _rank_products(self, task: AgentTask) -> AgentResult:
        """Rank products using multi-criteria AI scoring."""
        products = task.parameters.get("products", [])
        criteria = task.parameters.get("criteria", ["price", "quality", "style_match"])
        style = task.parameters.get("style", "modern")

        if not products:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["No products to rank"],
            )

        prompt = f"""Rank the following products based on these criteria: {', '.join(criteria)}

Design Style Context: {style}

Products to Rank:
{json.dumps(products, indent=2)}

Respond with JSON:
{{
    "ranked_products": [
        {{
            "rank": 1,
            "product": {{...original product data...}},
            "scores": {{
                "overall": 0.0-1.0,
                "price_value": 0.0-1.0,
                "quality": 0.0-1.0,
                "style_match": 0.0-1.0
            }},
            "reasoning": "Why this rank"
        }}
    ],
    "best_value": "Product name with best value",
    "best_quality": "Product name with best quality"
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=FURNITURE_SYSTEM_PROMPT,
            temperature=0.3,
        )

        try:
            rank_data = response.parse_json()
        except ValueError:
            rank_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"rankings": rank_data},
            token_usage=response.usage,
        )

    async def _compare_products(self, task: AgentTask) -> AgentResult:
        """Compare products side by side."""
        products = task.parameters.get("products", [])

        if len(products) < 2:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["At least 2 products required for comparison"],
            )

        prompt = f"""Compare these products side by side:

Products:
{json.dumps(products, indent=2)}

Respond with JSON:
{{
    "comparison": {{
        "criteria": ["Price", "Material", "Dimensions", "Style", "Durability", "Value"],
        "products": [
            {{
                "name": "Product name",
                "scores": {{"Price": "...", "Material": "...", ...}},
                "pros": ["Pro 1"],
                "cons": ["Con 1"]
            }}
        ]
    }},
    "winner": "Product name",
    "winner_reasoning": "Why this product wins",
    "best_for_budget": "Product name",
    "best_for_quality": "Product name"
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=FURNITURE_SYSTEM_PROMPT,
            temperature=0.3,
        )

        try:
            compare_data = response.parse_json()
        except ValueError:
            compare_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"comparison": compare_data},
            token_usage=response.usage,
        )
