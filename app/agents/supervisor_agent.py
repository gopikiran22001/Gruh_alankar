"""
Gruha Alankara — Supervisor Agent

The autonomous brain of the system. Uses Groq Reasoning to:
- Understand user intent
- Dynamically generate execution plans (DAGs)
- Select and orchestrate agents
- Handle failures and retries
- Aggregate results
- Coordinate with the Critic for validation

No hardcoded chains. No predefined workflows.
All orchestration is reasoning-driven.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.agents.schemas import (
    AgentResult,
    AgentTask,
    ExecutionPlan,
    TaskNode,
    TaskPriority,
    TaskStatusEnum,
    WorkflowContext,
)
from app.llm.groq_reasoning_client import GroqReasoningClient
from config.constants import (
    AgentName,
    SUPERVISOR_MAX_PLANNING_ITERATIONS,
    MAX_AGENT_RETRIES,
)
from config.logging_config import get_logger

logger = get_logger(__name__)


SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor Agent for "Gruha Alankara" — an AI-powered interior design platform.

You are the CEO and Project Manager. Your job is to understand user requests and create execution plans that coordinate specialized agents.

═══════════════════════════════════════
AVAILABLE AGENTS
═══════════════════════════════════════
{agent_capabilities}

═══════════════════════════════════════
YOUR RESPONSIBILITIES
═══════════════════════════════════════
1. UNDERSTAND the user's intent and extract key entities (style, budget, room type, etc.)
2. PLAN an execution strategy as a Directed Acyclic Graph (DAG) of tasks
3. SELECT the right agents for each task
4. DEFINE dependencies between tasks (what must complete before what)
5. IDENTIFY tasks that can run in parallel
6. CONSIDER user's memory/preferences from context

═══════════════════════════════════════
PLANNING RULES
═══════════════════════════════════════
- If the user uploads an image → include vision_agent first
- If design suggestions needed → include design_agent
- If product search needed → include web_agent, then furniture_agent
- If budget is mentioned → include budget_agent
- If booking/ordering → include booking_agent
- ALWAYS include memory_agent to store interaction
- ALWAYS end with buddy_agent to generate final response
- For complex requests, use parallel execution where possible
- Never create circular dependencies

═══════════════════════════════════════
TASK TYPES PER AGENT
═══════════════════════════════════════
- buddy_agent: chat, answer, generate_response, explain
- vision_agent: analyze_room, detect_objects, segment_room, extract_colors, analyze_lighting, full_analysis
- design_agent: generate_design, suggest_layout, generate_palette, recommend_decor
- web_agent: scrape_products, compare_prices, discover_trends, search_products
- furniture_agent: recommend_products, rank_products, compare_products
- budget_agent: estimate_budget, generate_breakdown, optimize_budget
- booking_agent: create_booking, update_status, track_order, list_bookings
- memory_agent: store_memory, retrieve_memory, update_memory, get_user_profile
- voice_agent: speech_to_text, text_to_speech
- critic_agent: validate, criticize, retry_if_needed

═══════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════
You MUST respond with a JSON execution plan."""


class SupervisorAgent(BaseAgent):
    """
    Autonomous Supervisor Agent — the reasoning brain of Gruha Alankara.

    Uses Groq Reasoning to dynamically plan, route, and orchestrate
    all other agents based on user intent.
    """

    name = AgentName.SUPERVISOR
    description = "Autonomous reasoning supervisor that plans, routes, and orchestrates all agents"
    supported_task_types = [
        "plan",
        "understand_intent",
        "create_plan",
        "replan",
    ]
    estimated_latency_s = 20.0

    def __init__(self) -> None:
        super().__init__()
        self._llm = GroqReasoningClient()

    def _get_capabilities(self) -> List[str]:
        return [
            "Understand user intent and extract entities",
            "Generate dynamic execution plans as DAGs",
            "Select and route to specialized agents",
            "Handle failures and trigger retries",
            "Coordinate multi-agent workflows",
            "Aggregate results from multiple agents",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "plan": self._create_plan,
            "understand_intent": self._understand_intent,
            "create_plan": self._create_plan,
            "replan": self._replan,
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

    async def _understand_intent(self, task: AgentTask) -> AgentResult:
        """Classify user intent and extract entities."""
        user_message = task.parameters.get("message", "")
        chat_history = task.parameters.get("chat_history", [])
        memory_context = task.parameters.get("memory_context", {})

        prompt = f"""Analyze this user message and extract the intent and entities.

User Message: "{user_message}"

Chat History (last 5):
{json.dumps(chat_history[-5:], indent=2) if chat_history else "None"}

User Memory/Preferences:
{json.dumps(memory_context, indent=2) if memory_context else "None"}

Respond with JSON:
{{
    "primary_intent": "room_analysis|design_request|furniture_search|budget_planning|booking|general_chat|voice_input|web_search|project_management|style_consultation|multi_intent",
    "sub_intents": ["list of sub-intents if multi_intent"],
    "entities": {{
        "room_type": "living_room|bedroom|kitchen|bathroom|...|null",
        "style": "scandinavian|modern|minimalist|...|null",
        "budget": null or number,
        "currency": "INR",
        "has_image": true/false,
        "products_mentioned": [],
        "sources_mentioned": [],
        "specific_request": "Brief description"
    }},
    "complexity": "simple|moderate|complex",
    "requires_agents": ["list of agent names needed"],
    "confidence": 0.0-1.0
}}"""

        response = self._llm.reason(prompt=prompt)

        try:
            intent_data = response.parse_json()
        except ValueError:
            intent_data = {
                "primary_intent": "general_chat",
                "entities": {},
                "complexity": "simple",
                "requires_agents": [AgentName.BUDDY],
                "confidence": 0.5,
            }

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "intent": intent_data,
                "reasoning": response.reasoning_content,
            },
            confidence_score=intent_data.get("confidence", 0.5),
            token_usage=response.usage,
        )

    async def _create_plan(self, task: AgentTask) -> AgentResult:
        """
        Create a dynamic execution plan based on user intent.
        This is the core planning method.
        """
        user_message = task.parameters.get("message", "")
        intent_data = task.parameters.get("intent", {})
        has_image = task.parameters.get("has_image", False)
        image_paths = task.parameters.get("image_paths", [])
        chat_history = task.parameters.get("chat_history", [])
        memory_context = task.parameters.get("memory_context", {})
        user_id = task.parameters.get("user_id", "")

        # Get agent capabilities from registry
        from app.agents.registry import agent_registry
        capabilities_summary = agent_registry.get_capabilities_summary()

        system_prompt = SUPERVISOR_SYSTEM_PROMPT.format(
            agent_capabilities=capabilities_summary,
        )

        prompt = f"""Create an execution plan for this user request.

═══════════════════════════════════════
USER REQUEST
═══════════════════════════════════════
Message: "{user_message}"
Has Image: {has_image}
Image Paths: {image_paths if image_paths else "None"}

═══════════════════════════════════════
INTENT ANALYSIS
═══════════════════════════════════════
{json.dumps(intent_data, indent=2) if intent_data else "Not analyzed yet"}

═══════════════════════════════════════
USER CONTEXT
═══════════════════════════════════════
User ID: {user_id}
Memory/Preferences: {json.dumps(memory_context, indent=2) if memory_context else "None"}
Recent Chat: {json.dumps(chat_history[-3:], indent=2) if chat_history else "None"}

═══════════════════════════════════════
INSTRUCTIONS
═══════════════════════════════════════
Generate an execution plan as a DAG of tasks. Each task runs on a specific agent.

Respond with JSON:
{{
    "plan_id": "unique_plan_id",
    "user_intent": "Summary of what the user wants",
    "reasoning": "Your step-by-step reasoning for why these agents are needed and in this order",
    "tasks": [
        {{
            "task_id": "t1",
            "agent_name": "agent_name",
            "task_type": "specific_task_type",
            "parameters": {{}},
            "depends_on": [],
            "priority": "low|medium|high|critical",
            "description": "What this task does",
            "estimated_duration_s": 10.0,
            "can_retry": true,
            "max_retries": 3
        }}
    ],
    "parallel_groups": [["t1", "t2"], ["t3"]],
    "estimated_total_duration_s": 0,
    "requires_human_input": false,
    "human_input_prompt": null
}}

CRITICAL: Generate the tasks in dependency order. Tasks with no depends_on are root tasks.
CRITICAL: Include buddy_agent as the LAST task with task_type "generate_response".
CRITICAL: Include memory_agent to store this interaction."""

        response = self._llm.reason(
            prompt=prompt,
            context=system_prompt,
            max_tokens=8192,
        )

        try:
            plan_data = response.parse_json()

            # Ensure plan_id
            if not plan_data.get("plan_id"):
                plan_data["plan_id"] = f"plan_{uuid.uuid4().hex[:8]}"

            # Validate and construct ExecutionPlan
            plan = ExecutionPlan(**plan_data)

            logger.info(
                "execution_plan_created",
                plan_id=plan.plan_id,
                task_count=len(plan.tasks),
                parallel_groups=len(plan.parallel_groups),
            )

        except (ValueError, Exception) as e:
            logger.warning("plan_parse_failed", error=str(e))
            # Fallback: simple chat plan
            plan = self._create_fallback_plan(user_message, has_image)

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "plan": plan.model_dump(),
                "reasoning": response.reasoning_content if hasattr(response, 'reasoning_content') else "",
            },
            token_usage=response.usage if hasattr(response, 'usage') else {},
        )

    async def _replan(self, task: AgentTask) -> AgentResult:
        """
        Re-plan after a failure or critic rejection.
        Takes the original plan and failure info to generate a corrected plan.
        """
        original_plan = task.parameters.get("original_plan", {})
        failure_info = task.parameters.get("failure_info", {})
        critic_feedback = task.parameters.get("critic_feedback", {})
        retry_count = task.parameters.get("retry_count", 0)

        if retry_count >= SUPERVISOR_MAX_PLANNING_ITERATIONS:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Maximum planning iterations exceeded"],
            )

        prompt = f"""An execution plan failed and needs to be revised.

Original Plan:
{json.dumps(original_plan, indent=2)}

Failure Information:
{json.dumps(failure_info, indent=2, default=str)}

Critic Feedback:
{json.dumps(critic_feedback, indent=2, default=str)}

Retry Count: {retry_count}/{SUPERVISOR_MAX_PLANNING_ITERATIONS}

Generate a REVISED execution plan that addresses the failures.
Only re-run the tasks that failed or need modification.
Keep successful task results.

Respond with the same JSON format as the original plan."""

        response = self._llm.reason(prompt=prompt)

        try:
            plan_data = response.parse_json()
            plan_data["plan_id"] = f"replan_{uuid.uuid4().hex[:8]}"
            plan = ExecutionPlan(**plan_data)
        except (ValueError, Exception):
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Failed to generate revised plan"],
            )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "plan": plan.model_dump(),
                "reasoning": response.reasoning_content,
                "is_replan": True,
                "retry_count": retry_count + 1,
            },
            token_usage=response.usage,
        )

    def _create_fallback_plan(
        self,
        user_message: str,
        has_image: bool = False,
    ) -> ExecutionPlan:
        """Create a simple fallback plan when planning fails."""
        tasks = []

        if has_image:
            tasks.append(TaskNode(
                task_id="t_vision",
                agent_name=AgentName.VISION,
                task_type="full_analysis",
                parameters={},
                depends_on=[],
                priority=TaskPriority.HIGH,
                description="Analyze uploaded room image",
            ))

        # Memory retrieval
        tasks.append(TaskNode(
            task_id="t_memory",
            agent_name=AgentName.MEMORY,
            task_type="retrieve_memory",
            parameters={"query": user_message},
            depends_on=[],
            priority=TaskPriority.MEDIUM,
            description="Retrieve relevant user memories",
        ))

        # Buddy response (always last)
        depends = [t.task_id for t in tasks]
        tasks.append(TaskNode(
            task_id="t_buddy",
            agent_name=AgentName.BUDDY,
            task_type="chat",
            parameters={"message": user_message},
            depends_on=depends,
            priority=TaskPriority.HIGH,
            description="Generate user response",
        ))

        # Memory store
        tasks.append(TaskNode(
            task_id="t_memory_store",
            agent_name=AgentName.MEMORY,
            task_type="store_memory",
            parameters={"content": user_message},
            depends_on=["t_buddy"],
            priority=TaskPriority.LOW,
            description="Store conversation in memory",
        ))

        return ExecutionPlan(
            plan_id=f"fallback_{uuid.uuid4().hex[:8]}",
            user_intent="General conversation (fallback plan)",
            reasoning="Fallback plan due to planning failure. Running basic chat flow.",
            tasks=tasks,
            parallel_groups=[["t_memory"]] + ([["t_vision"]] if has_image else []),
        )
