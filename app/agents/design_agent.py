"""
Gruha Alankara — Design Agent

Generates interior design proposals, layout suggestions,
color palettes, and decor recommendations using Groq Llama-3.3-70b.
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

DESIGN_SYSTEM_PROMPT = """You are an expert interior designer with deep knowledge of:
- All major design styles (Scandinavian, Modern, Minimalist, Industrial, Bohemian, Traditional Indian, Contemporary, etc.)
- Space optimization and furniture arrangement
- Color theory and palette generation
- Indian market furniture and decor
- Budget-conscious design solutions

You provide detailed, actionable design recommendations with specific product suggestions.
Always consider the client's budget, room dimensions, existing furniture, and personal preferences.
Respond with structured JSON when asked for designs, layouts, or palettes."""


class DesignAgent(BaseAgent):
    """
    Interior design agent powered by Groq Llama-3.3-70b and Groq Llama-3.1-8b.

    Responsibilities:
    - Generate complete design proposals
    - Suggest room layouts and furniture arrangements
    - Create color palettes matching design styles
    - Recommend decor items and accessories
    """

    name = AgentName.DESIGN
    description = "Generates interior design proposals, layouts, color palettes, and decor suggestions"
    supported_task_types = [
        "generate_design",
        "suggest_layout",
        "generate_palette",
        "recommend_decor",
    ]
    estimated_latency_s = 20.0

    def __init__(self) -> None:
        super().__init__()
        from app.llm.groq_client import GroqClient
        self._llm = GroqClient(
            api_key=settings.groq_design.API_KEY,
            api_url=settings.groq_design.API_URL,
            model=settings.groq_design.MODEL,
        )

    def _get_capabilities(self) -> List[str]:
        return [
            "Generate complete interior design proposals",
            "Create room layout and furniture arrangement plans",
            "Generate harmonious color palettes for any style",
            "Recommend decor items, accessories, and finishing touches",
            "Optimize space utilization for small rooms",
            "Adapt designs to Indian market availability and aesthetics",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "generate_design": self._generate_design,
            "suggest_layout": self._suggest_layout,
            "generate_palette": self._generate_palette,
            "recommend_decor": self._recommend_decor,
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

    async def _generate_design(self, task: AgentTask) -> AgentResult:
        """Generate a complete design proposal."""
        room_analysis = task.context.get("room_analysis", {})
        style = task.parameters.get("style", "modern")
        budget = task.constraints.get("budget")
        room_type = task.parameters.get("room_type", "living room")
        preferences = task.parameters.get("preferences", {})

        prompt = f"""Generate a complete interior design proposal for a {room_type}.

Style: {style}
Budget: {'₹' + str(budget) if budget else 'Not specified'}
Room Analysis: {json.dumps(room_analysis, indent=2) if room_analysis else 'No room image provided'}
User Preferences: {json.dumps(preferences, indent=2) if preferences else 'None specified'}

Respond with a JSON object containing:
{{
    "design_title": "Creative name for the design",
    "style_description": "Detailed description of the design style and mood",
    "color_scheme": {{
        "primary": {{"hex": "#...", "name": "..."}},
        "secondary": {{"hex": "#...", "name": "..."}},
        "accent": {{"hex": "#...", "name": "..."}},
        "neutral": {{"hex": "#...", "name": "..."}}
    }},
    "furniture_list": [
        {{
            "item": "Item name",
            "description": "Description",
            "estimated_price_inr": 0,
            "priority": "essential|recommended|optional",
            "placement": "Where to place it"
        }}
    ],
    "decor_suggestions": [
        {{
            "item": "Item name",
            "description": "Description",
            "estimated_price_inr": 0
        }}
    ],
    "layout_tips": ["Tip 1", "Tip 2"],
    "estimated_total_inr": 0,
    "design_rationale": "Why this design works for the space"
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=DESIGN_SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=4096,
        )

        try:
            design_data = response.parse_json()
        except ValueError:
            design_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"design": design_data},
            token_usage=response.usage,
        )

    async def _suggest_layout(self, task: AgentTask) -> AgentResult:
        """Suggest room layout and furniture arrangement."""
        room_dims = task.parameters.get("room_dimensions", {})
        furniture_list = task.parameters.get("furniture_list", [])
        room_type = task.parameters.get("room_type", "living room")

        prompt = f"""Suggest an optimal furniture layout for a {room_type}.

Room Dimensions: {json.dumps(room_dims) if room_dims else 'Unknown'}
Available Furniture: {json.dumps(furniture_list) if furniture_list else 'Standard furniture set'}

Respond with a JSON object:
{{
    "layout_name": "Name for this layout",
    "arrangement": [
        {{
            "item": "Furniture item",
            "position": "Description of placement",
            "wall": "Which wall or area",
            "rotation": "Orientation"
        }}
    ],
    "traffic_flow": "Description of movement paths",
    "focal_point": "Main visual anchor",
    "space_efficiency_score": 0.0-1.0,
    "tips": ["Layout tip 1", "Layout tip 2"]
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=DESIGN_SYSTEM_PROMPT,
            temperature=0.5,
        )

        try:
            layout_data = response.parse_json()
        except ValueError:
            layout_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"layout": layout_data},
            token_usage=response.usage,
        )

    async def _generate_palette(self, task: AgentTask) -> AgentResult:
        """Generate a color palette for the design."""
        style = task.parameters.get("style", "modern")
        room_colors = task.context.get("color_analysis", {})
        mood = task.parameters.get("mood", "calm and inviting")

        prompt = f"""Generate a harmonious color palette for a {style} interior design.

Desired Mood: {mood}
Existing Room Colors: {json.dumps(room_colors) if room_colors else 'Starting fresh'}

Respond with a JSON object:
{{
    "palette_name": "Name for this palette",
    "colors": [
        {{
            "role": "primary|secondary|accent|neutral|background",
            "hex": "#xxxxxx",
            "name": "Color name",
            "usage": "Where to use this color"
        }}
    ],
    "wall_colors": {{
        "main_walls": {{"hex": "#...", "finish": "matte|eggshell|satin"}},
        "accent_wall": {{"hex": "#...", "finish": "..."}}
    }},
    "complementary_materials": ["Material 1", "Material 2"],
    "avoid_colors": ["Colors to avoid and why"]
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=DESIGN_SYSTEM_PROMPT,
            temperature=0.6,
        )

        try:
            palette_data = response.parse_json()
        except ValueError:
            palette_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"palette": palette_data},
            token_usage=response.usage,
        )

    async def _recommend_decor(self, task: AgentTask) -> AgentResult:
        """Recommend decor items and accessories."""
        style = task.parameters.get("style", "modern")
        budget = task.constraints.get("budget")
        room_type = task.parameters.get("room_type", "living room")

        prompt = f"""Recommend decor items and accessories for a {style} {room_type}.

Budget for decor: {'₹' + str(budget) if budget else 'Not specified'}

Respond with a JSON object:
{{
    "categories": [
        {{
            "category": "Category name (e.g., Wall Art, Plants, Textiles)",
            "items": [
                {{
                    "name": "Item name",
                    "description": "Description",
                    "estimated_price_inr": 0,
                    "where_to_buy": ["Store/website names"],
                    "placement_tip": "Where and how to place"
                }}
            ]
        }}
    ],
    "styling_tips": ["Tip 1", "Tip 2"],
    "estimated_total_inr": 0
}}"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=DESIGN_SYSTEM_PROMPT,
            temperature=0.7,
        )

        try:
            decor_data = response.parse_json()
        except ValueError:
            decor_data = {"raw_response": response.content}

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"decor": decor_data},
            token_usage=response.usage,
        )
