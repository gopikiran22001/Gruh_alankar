"""
Gruha Alankara — Buddy Agent

User-facing conversational agent. Handles chat interactions,
response generation, and multilingual support using Groq Llama-3.3-70b.
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

BUDDY_SYSTEM_PROMPT = """You are Gruha, a friendly and knowledgeable interior design assistant for "Gruha Alankara" — an AI-powered interior design platform.

Your personality:
- Warm, approachable, and enthusiastic about design
- Expert knowledge of interior design, Indian market, and home decor
- Speaks naturally in the user's preferred language (English, Hindi, Kannada, etc.)
- Explains complex design concepts in simple terms
- Always positive and solution-oriented

Your role:
- Greet users and understand their design needs
- Present design results from other agents in a user-friendly way
- Answer questions about interior design
- Guide users through the design process
- Summarize complex multi-agent results into clear, actionable responses

When presenting results from other agents, format them beautifully with:
- Clear sections and headings
- Bullet points for lists
- Price ranges in Indian Rupees (₹)
- Actionable next steps"""


class BuddyAgent(BaseAgent):
    """
    User-facing conversational agent.

    The Buddy Agent is the primary interface between the user
    and the rest of the system. It:
    - Handles casual conversation
    - Presents multi-agent results in user-friendly format
    - Provides design guidance and explanations
    - Supports multiple languages
    """

    name = AgentName.BUDDY
    description = "User-facing conversational agent for chat, explanations, and response generation"
    supported_task_types = [
        "chat",
        "answer",
        "generate_response",
        "explain",
    ]
    estimated_latency_s = 8.0

    def __init__(self) -> None:
        super().__init__()
        from app.llm.groq_client import GroqClient
        self._llm = GroqClient(
            api_key=settings.groq_buddy.API_KEY,
            api_url=settings.groq_buddy.API_URL,
            model=settings.groq_buddy.MODEL,
        )

    def _get_capabilities(self) -> List[str]:
        return [
            "Natural conversation about interior design",
            "Present multi-agent results in user-friendly format",
            "Answer design questions and provide guidance",
            "Multilingual support (English, Hindi, Kannada, etc.)",
            "Summarize complex design proposals",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "chat": self._chat,
            "answer": self._answer,
            "generate_response": self._generate_response,
            "explain": self._explain,
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

    async def _chat(self, task: AgentTask) -> AgentResult:
        """Handle a casual chat message."""
        user_message = task.parameters.get("message", "")
        chat_history = task.parameters.get("chat_history", [])
        user_preferences = task.context.get("preferences", {})

        context_note = ""
        if user_preferences:
            context_note = f"\n\nUser preferences: {json.dumps(user_preferences)}"

        response = self._llm.chat(
            user_message=user_message,
            system_prompt=BUDDY_SYSTEM_PROMPT + context_note,
            chat_history=chat_history[-10:],  # Keep last 10 messages for context
            temperature=0.7,
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "response": response.content,
                "type": "chat",
            },
            token_usage=response.usage,
        )

    async def _answer(self, task: AgentTask) -> AgentResult:
        """Answer a specific question with data-backed response."""
        question = task.parameters.get("question", "")
        data = task.parameters.get("data", {})

        prompt = f"""Answer the following question using the provided data.

Question: {question}

Data:
{json.dumps(data, indent=2)}

Provide a clear, helpful answer in the user's language. Format nicely."""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=BUDDY_SYSTEM_PROMPT,
            temperature=0.5,
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "response": response.content,
                "type": "answer",
            },
            token_usage=response.usage,
        )

    async def _generate_response(self, task: AgentTask) -> AgentResult:
        """
        Synthesize multi-agent outputs into a user-friendly response.
        This is the final step in most workflows.
        """
        user_query = task.parameters.get("user_query", "")
        agent_outputs = task.context.get("agent_results", {})

        # Format agent outputs for the LLM
        formatted_outputs = self._format_agent_outputs(agent_outputs)

        prompt = f"""The user asked: "{user_query}"

Multiple specialized agents have produced the following results:

{formatted_outputs}

Synthesize ALL these results into a single, comprehensive, beautifully formatted response for the user.

Guidelines:
1. Start with a brief, warm overview
2. Present design suggestions with clear structure
3. Show product recommendations with prices in ₹
4. Include budget breakdown if available
5. Provide actionable next steps
6. Be enthusiastic but professional
7. Don't mention "agents" or "system" — present as if you did the work"""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=BUDDY_SYSTEM_PROMPT,
            temperature=0.6,
            max_tokens=4096,
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "response": response.content,
                "type": "synthesized_response",
            },
            token_usage=response.usage,
        )

    async def _explain(self, task: AgentTask) -> AgentResult:
        """Explain a design concept or decision."""
        topic = task.parameters.get("topic", "")
        context = task.parameters.get("context", "")

        prompt = f"""Explain the following interior design topic/concept:

Topic: {topic}
Context: {context if context else 'General explanation'}

Provide a clear, educational, and engaging explanation suitable for someone new to interior design."""

        response = self._llm.chat(
            user_message=prompt,
            system_prompt=BUDDY_SYSTEM_PROMPT,
            temperature=0.7,
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "response": response.content,
                "type": "explanation",
            },
            token_usage=response.usage,
        )

    @staticmethod
    def _format_agent_outputs(outputs: Dict[str, Any]) -> str:
        """Format agent results for the synthesis prompt."""
        sections = []
        for agent_name, result in outputs.items():
            if isinstance(result, dict):
                data = result.get("data", result)
            else:
                data = result

            sections.append(
                f"--- {agent_name.replace('_', ' ').title()} ---\n"
                f"{json.dumps(data, indent=2, default=str)}\n"
            )
        return "\n".join(sections) if sections else "No agent outputs available."
