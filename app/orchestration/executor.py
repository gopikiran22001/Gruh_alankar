"""
Gruha Alankara — Workflow Executor

Runs dynamically-built LangGraph workflows end-to-end:
1. Supervisor plans → 2. Graph is built → 3. Graph executes → 4. Results returned

This is the main entry point for all autonomous agent workflows.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from app.agents.registry import agent_registry
from app.agents.schemas import AgentTask, TaskStatusEnum
from app.database.mongo import save_chat_message, log_agent_execution
from app.database.redis_cache import cache
from app.orchestration.graph_builder import DynamicGraphBuilder
from app.orchestration.nodes import create_supervisor_node
from app.orchestration.workflow_state import WorkflowState
from config.constants import AgentName, MAX_AGENT_RETRIES
from config.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowExecutor:
    """
    Orchestrates the full autonomous workflow:

    1. Receive user message
    2. Supervisor understands intent and creates execution plan
    3. Graph Builder converts plan to LangGraph StateGraph
    4. Execute the graph
    5. Return final response

    Handles retries, caching, and progress tracking.
    """

    def __init__(self) -> None:
        self._graph_builder = DynamicGraphBuilder()

    async def run_workflow(
        self,
        user_id: str,
        session_id: str,
        message: str,
        image_paths: Optional[List[str]] = None,
        audio_path: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        budget: Optional[float] = None,
        style: Optional[str] = None,
        room_type: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a full autonomous workflow.

        This is the main entry point. It:
        1. Gets the Supervisor to plan
        2. Builds a dynamic graph
        3. Executes the graph
        4. Returns the final response

        Args:
            user_id: The user's ID.
            session_id: Current chat session ID.
            message: User's message.
            image_paths: Optional uploaded image paths.
            audio_path: Optional audio file path (voice input).
            chat_history: Recent chat history.
            budget: User's budget constraint.
            style: Preferred design style.
            room_type: Type of room.
            project_id: Optional project ID.

        Returns:
            Dict with final response, agent results, and metadata.
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        logger.info(
            "workflow_started",
            workflow_id=workflow_id,
            user_id=user_id,
            message_preview=message[:100],
        )

        # Save user message to chat history
        try:
            save_chat_message(user_id, session_id, "user", message)
        except Exception:
            pass

        # Initialize workflow state
        initial_state: WorkflowState = {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "session_id": session_id,
            "plan_id": "",
            "user_message": message,
            "image_paths": image_paths or [],
            "audio_path": audio_path,
            "user_intent": {},
            "execution_plan": {},
            "budget": budget,
            "style": style,
            "room_type": room_type,
            "preferences": {},
            "chat_history": chat_history or [],
            "memory_context": {},
            "agent_results": {},
            "current_task_id": "",
            "current_agent": "",
            "tasks_completed": [],
            "tasks_failed": [],
            "critic_feedback": {},
            "is_validated": False,
            "retry_count": 0,
            "max_retries": MAX_AGENT_RETRIES,
            "retry_agents": {},
            "final_response": "",
            "status": "running",
            "errors": [],
            "total_duration_ms": 0,
            "total_tokens_used": 0,
        }

        try:
            # ── Step 1: Handle voice input ──
            if audio_path:
                initial_state = await self._handle_voice_input(
                    initial_state, audio_path
                )

            # ── Step 2: Retrieve user memory ──
            initial_state = await self._retrieve_memory(initial_state)

            # ── Step 3: Supervisor planning ──
            plan = await self._supervisor_plan(initial_state)
            initial_state["execution_plan"] = plan
            initial_state["plan_id"] = plan.get("plan_id", "")

            # ── Step 4: Build and execute graph ──
            tasks = plan.get("tasks", [])

            if self._is_complex_workflow(tasks):
                # Use critic validation for complex workflows
                compiled_graph = self._graph_builder.build_graph_with_critic(plan)
            else:
                compiled_graph = self._graph_builder.build_graph(plan)

            # ── Step 5: Execute ──
            final_state = compiled_graph.invoke(initial_state)

            # ── Step 6: Extract results ──
            duration_ms = (time.time() - start_time) * 1000
            final_response = final_state.get("final_response", "")

            # If no final response was generated, create one
            if not final_response:
                final_response = await self._generate_fallback_response(
                    message, final_state.get("agent_results", {})
                )

            # Save assistant response
            try:
                save_chat_message(user_id, session_id, "assistant", final_response)
            except Exception:
                pass

            # Store interaction in memory
            await self._store_memory(initial_state, final_response)

            # Cache workflow state
            cache.cache_workflow_state(workflow_id, {
                "status": "completed",
                "response": final_response[:500],
            })

            result = {
                "workflow_id": workflow_id,
                "response": final_response,
                "status": "success",
                "agent_results": self._sanitize_results(
                    final_state.get("agent_results", {})
                ),
                "execution_plan": plan,
                "critic_feedback": final_state.get("critic_feedback", {}),
                "metadata": {
                    "duration_ms": round(duration_ms, 1),
                    "total_tokens": final_state.get("total_tokens_used", 0),
                    "tasks_completed": final_state.get("tasks_completed", []),
                    "tasks_failed": final_state.get("tasks_failed", []),
                    "retry_count": final_state.get("retry_count", 0),
                },
            }

            logger.info(
                "workflow_completed",
                workflow_id=workflow_id,
                duration_ms=round(duration_ms, 1),
                tasks_completed=len(final_state.get("tasks_completed", [])),
                tasks_failed=len(final_state.get("tasks_failed", [])),
            )

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "workflow_failed",
                workflow_id=workflow_id,
                error=str(e),
                duration_ms=round(duration_ms, 1),
            )

            # Fallback response
            fallback_response = await self._generate_error_response(message, str(e))

            return {
                "workflow_id": workflow_id,
                "response": fallback_response,
                "status": "error",
                "error": str(e),
                "metadata": {
                    "duration_ms": round(duration_ms, 1),
                },
            }

    async def _supervisor_plan(self, state: WorkflowState) -> Dict[str, Any]:
        """Get the Supervisor to create an execution plan."""
        supervisor = agent_registry.get(AgentName.SUPERVISOR)
        if not supervisor:
            logger.warning("supervisor_not_found, using fallback")
            return {"tasks": [], "plan_id": "fallback"}

        plan_task = AgentTask(
            task_id="supervisor_plan",
            task_type="create_plan",
            agent_name=AgentName.SUPERVISOR,
            parameters={
                "message": state["user_message"],
                "has_image": bool(state.get("image_paths")),
                "image_paths": state.get("image_paths", []),
                "chat_history": state.get("chat_history", []),
                "memory_context": state.get("memory_context", {}),
                "user_id": state.get("user_id", ""),
            },
            metadata={"workflow_id": state["workflow_id"]},
        )

        result = await supervisor.run(plan_task)

        if result.is_success:
            return result.data.get("plan", {})
        else:
            logger.warning("supervisor_planning_failed", errors=result.errors)
            # Return fallback plan
            from app.agents.supervisor_agent import SupervisorAgent
            sv = SupervisorAgent()
            fallback = sv._create_fallback_plan(
                state["user_message"],
                bool(state.get("image_paths")),
            )
            return fallback.model_dump()

    async def _handle_voice_input(
        self, state: WorkflowState, audio_path: str
    ) -> WorkflowState:
        """Transcribe voice input and update the message."""
        voice_agent = agent_registry.get(AgentName.VOICE)
        if not voice_agent:
            return state

        task = AgentTask(
            task_id="voice_transcribe",
            task_type="speech_to_text",
            agent_name=AgentName.VOICE,
            parameters={"audio_path": audio_path},
            metadata={"workflow_id": state["workflow_id"]},
        )

        result = await voice_agent.run(task)
        if result.is_success:
            transcript = result.data.get("transcript", "")
            if transcript:
                state["user_message"] = transcript
                logger.info("voice_transcribed", length=len(transcript))

        return state

    async def _retrieve_memory(self, state: WorkflowState) -> WorkflowState:
        """Retrieve relevant memories for context."""
        memory_agent = agent_registry.get(AgentName.MEMORY)
        if not memory_agent:
            return state

        try:
            task = AgentTask(
                task_id="memory_retrieve",
                task_type="retrieve_memory",
                agent_name=AgentName.MEMORY,
                parameters={
                    "user_id": state["user_id"],
                    "query": state["user_message"],
                    "top_k": 5,
                },
                metadata={"workflow_id": state["workflow_id"]},
            )

            result = await memory_agent.run(task)
            if result.is_success:
                memories = result.data.get("memories", [])
                state["memory_context"] = {
                    "relevant_memories": memories,
                }
        except Exception as e:
            logger.warning("memory_retrieval_failed", error=str(e))

        return state

    async def _store_memory(
        self, state: WorkflowState, response: str
    ) -> None:
        """Store the interaction in memory."""
        memory_agent = agent_registry.get(AgentName.MEMORY)
        if not memory_agent:
            return

        try:
            content = f"User: {state['user_message']}\nAssistant: {response[:500]}"
            task = AgentTask(
                task_id="memory_store",
                task_type="store_memory",
                agent_name=AgentName.MEMORY,
                parameters={
                    "user_id": state["user_id"],
                    "content": content,
                    "memory_type": "conversation",
                },
                metadata={"workflow_id": state["workflow_id"]},
            )
            await memory_agent.run(task)
        except Exception as e:
            logger.warning("memory_store_failed", error=str(e))

    async def _generate_fallback_response(
        self, message: str, agent_results: Dict[str, Any]
    ) -> str:
        """Generate a response when the normal flow doesn't produce one."""
        buddy = agent_registry.get(AgentName.BUDDY)
        if not buddy:
            return "I apologize, but I'm having trouble generating a response right now. Please try again."

        task = AgentTask(
            task_id="fallback_response",
            task_type="generate_response",
            agent_name=AgentName.BUDDY,
            parameters={"user_query": message},
            context={"agent_results": agent_results},
        )

        result = await buddy.run(task)
        if result.is_success:
            return result.data.get("response", "")
        return "I apologize, but I'm having trouble processing your request. Please try again."

    async def _generate_error_response(self, message: str, error: str) -> str:
        """Generate a user-friendly error response."""
        buddy = agent_registry.get(AgentName.BUDDY)
        if not buddy:
            return (
                "I'm sorry, I encountered an issue while processing your request. "
                "Could you please try again? If the problem persists, try simplifying your request."
            )

        task = AgentTask(
            task_id="error_response",
            task_type="chat",
            agent_name=AgentName.BUDDY,
            parameters={
                "message": (
                    f"The user asked: '{message}' but an error occurred. "
                    f"Generate a polite, helpful response acknowledging the issue "
                    f"and suggesting they try again. Do not mention technical details."
                ),
            },
        )

        result = await buddy.run(task)
        if result.is_success:
            return result.data.get("response", "")
        return "I'm sorry, something went wrong. Please try again."

    @staticmethod
    def _is_complex_workflow(tasks: List[Dict[str, Any]]) -> bool:
        """Determine if a workflow needs critic validation."""
        # Increase threshold to reduce unnecessary critic validation
        if len(tasks) <= 4:
            return False
        agent_names = {t.get("agent_name") for t in tasks}
        complex_agents = {"design_agent", "furniture_agent", "budget_agent", "booking_agent"}
        # Only use critic if there are multiple complex agents
        return len(agent_names & complex_agents) >= 2

    @staticmethod
    def _sanitize_results(results: Dict[str, Any]) -> Dict[str, Any]:
        """Remove large binary data from results for API response."""
        sanitized = {}
        for key, value in results.items():
            if isinstance(value, dict):
                sanitized[key] = {
                    "status": value.get("status"),
                    "data_keys": list(value.get("data", {}).keys()),
                    "confidence": value.get("confidence_score"),
                    "duration_ms": value.get("duration_ms"),
                }
            else:
                sanitized[key] = str(value)[:200]
        return sanitized


# Module-level instance
workflow_executor = WorkflowExecutor()
