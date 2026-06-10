"""
Gruha Alankara — Node Factory

Creates LangGraph-compatible node functions that wrap each agent's
execute() method. These are the building blocks for dynamic graphs.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

from app.agents.registry import agent_registry
from app.agents.schemas import AgentTask, TaskPriority, TaskStatusEnum
from app.orchestration.workflow_state import WorkflowState
from config.logging_config import get_logger

logger = get_logger(__name__)


def create_agent_node(agent_name: str, task_config: Dict[str, Any]):
    """
    Factory function that creates a LangGraph node function for an agent.

    Args:
        agent_name: Name of the agent to wrap.
        task_config: Task configuration from the execution plan.

    Returns:
        A callable node function compatible with LangGraph StateGraph.
    """

    def agent_node(state: WorkflowState) -> Dict[str, Any]:
        """LangGraph node that executes an agent task."""
        agent = agent_registry.get_or_raise(agent_name)

        # Build AgentTask from state and config
        task = AgentTask(
            task_id=task_config.get("task_id", f"{agent_name}_task"),
            task_type=task_config.get("task_type", "execute"),
            agent_name=agent_name,
            parameters=_build_parameters(state, task_config),
            context=_build_context(state, agent_name),
            constraints=_build_constraints(state),
            priority=TaskPriority(task_config.get("priority", "medium")),
            metadata={
                "workflow_id": state.get("workflow_id", ""),
                "user_id": state.get("user_id", ""),
            },
        )

        # Execute the agent - handle both sync and async contexts
        try:
            # Try to get the current running loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context (Flask), run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, agent.run(task))
                    result = future.result(timeout=300)  # 5 minute timeout
            except RuntimeError:
                # No running loop, safe to create new one
                result = asyncio.run(agent.run(task))
        except concurrent.futures.TimeoutError:
            logger.error(
                "agent_node_timeout",
                agent=agent_name,
                task_id=task_config.get("task_id")
            )
            from app.agents.schemas import AgentResult
            result = AgentResult(
                task_id=task.task_id,
                agent_name=agent_name,
                status=TaskStatusEnum.FAILED,
                errors=["Agent execution timeout after 5 minutes"]
            )
        except Exception as e:
            # Handle execution errors gracefully
            logger.error(
                "agent_node_execution_error",
                agent=agent_name,
                task_id=task_config.get("task_id"),
                error=str(e)
            )
            # Create a failed result
            from app.agents.schemas import AgentResult
            result = AgentResult(
                task_id=task.task_id,
                agent_name=agent_name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Execution error: {str(e)}"]
            )

        # Update state with results
        agent_results = {agent_name: result.model_dump()}

        tasks_completed = list(state.get("tasks_completed", []))
        tasks_failed = list(state.get("tasks_failed", []))
        errors = list(state.get("errors", []))

        if result.is_success:
            tasks_completed.append(task_config.get("task_id", agent_name))
        else:
            tasks_failed.append(task_config.get("task_id", agent_name))
            errors.extend(result.errors)

        # Calculate token usage
        total_tokens = state.get("total_tokens_used", 0)
        total_tokens += result.token_usage.get("total_tokens", 0)

        update: Dict[str, Any] = {
            "agent_results": agent_results,  # Will be merged via custom reducer
            "tasks_completed": tasks_completed,
            "tasks_failed": tasks_failed,
            "errors": errors,
            "current_agent": agent_name,
            "current_task_id": task_config.get("task_id", ""),
            "total_tokens_used": total_tokens,
        }

        # Special handling for specific agents
        if agent_name == "buddy_agent" and result.is_success:
            response = result.data.get("response", "")
            if response:
                update["final_response"] = response

        if agent_name == "supervisor_agent" and result.is_success:
            plan = result.data.get("plan", {})
            if plan:
                update["execution_plan"] = plan
            intent = result.data.get("intent", {})
            if intent:
                update["user_intent"] = intent

        if agent_name == "critic_agent" and result.is_success:
            feedback = result.data.get("feedback", {})
            update["critic_feedback"] = feedback
            update["is_validated"] = feedback.get("is_approved", False)

        if agent_name == "memory_agent" and result.is_success:
            memories = result.data.get("memories", [])
            if memories:
                update["memory_context"] = {"relevant_memories": memories}

        logger.info(
            "node_executed",
            agent=agent_name,
            task_id=task_config.get("task_id"),
            status=result.status.value,
            duration_ms=round(result.duration_ms, 1),
        )

        return update

    # Set a readable name on the function for LangGraph
    agent_node.__name__ = f"node_{agent_name}"
    return agent_node


def create_supervisor_node():
    """Create the supervisor planning node."""
    def supervisor_plan_node(state: WorkflowState) -> Dict[str, Any]:
        """Supervisor plans the execution."""
        from app.agents.supervisor_agent import SupervisorAgent

        supervisor = SupervisorAgent()

        # First, understand intent
        intent_task = AgentTask(
            task_id="supervisor_intent",
            task_type="understand_intent",
            agent_name="supervisor_agent",
            parameters={
                "message": state.get("user_message", ""),
                "chat_history": state.get("chat_history", []),
                "memory_context": state.get("memory_context", {}),
            },
            metadata={"workflow_id": state.get("workflow_id", "")},
        )

        intent_result = asyncio.run(supervisor.run(intent_task))
        intent_data = intent_result.data.get("intent", {})

        # Then, create plan
        plan_task = AgentTask(
            task_id="supervisor_plan",
            task_type="create_plan",
            agent_name="supervisor_agent",
            parameters={
                "message": state.get("user_message", ""),
                "intent": intent_data,
                "has_image": bool(state.get("image_paths")),
                "image_paths": state.get("image_paths", []),
                "chat_history": state.get("chat_history", []),
                "memory_context": state.get("memory_context", {}),
                "user_id": state.get("user_id", ""),
            },
            metadata={"workflow_id": state.get("workflow_id", "")},
        )

        plan_result = asyncio.run(supervisor.run(plan_task))

        return {
            "user_intent": intent_data,
            "execution_plan": plan_result.data.get("plan", {}),
            "status": "planned",
        }

    return supervisor_plan_node


def create_critic_node():
    """Create the critic validation node."""
    return create_agent_node("critic_agent", {
        "task_id": "critic_validate",
        "task_type": "validate",
        "priority": "high",
    })


def create_response_node():
    """Create the final response generation node (Buddy Agent)."""
    return create_agent_node("buddy_agent", {
        "task_id": "generate_response",
        "task_type": "generate_response",
        "priority": "high",
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_parameters(state: WorkflowState, task_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build task parameters from state and config."""
    params = dict(task_config.get("parameters", {}))

    # Inject common parameters
    params.setdefault("message", state.get("user_message", ""))
    params.setdefault("user_id", state.get("user_id", ""))

    if state.get("image_paths"):
        params.setdefault("image_path", state["image_paths"][0])
        params.setdefault("image_paths", state["image_paths"])

    if state.get("style"):
        params.setdefault("style", state["style"])

    if state.get("room_type"):
        params.setdefault("room_type", state["room_type"])

    return params


def _build_context(state: WorkflowState, agent_name: str) -> Dict[str, Any]:
    """Build context from previous agent results."""
    context: Dict[str, Any] = {}
    agent_results = state.get("agent_results", {})

    # Include relevant previous results
    for prev_agent, prev_result in agent_results.items():
        if isinstance(prev_result, dict) and prev_result.get("status") == "success":
            data = prev_result.get("data", {})
            # Map to context keys
            if prev_agent == "vision_agent":
                context["room_analysis"] = data
                context["color_analysis"] = data.get("color_analysis", {})
            elif prev_agent == "design_agent":
                context["design"] = data.get("design", {})
            elif prev_agent == "web_agent":
                context["products"] = data.get("products", [])
            elif prev_agent == "furniture_agent":
                context["recommendations"] = data.get("recommendations", {})
            elif prev_agent == "budget_agent":
                context["budget"] = data.get("budget", {})
            elif prev_agent == "memory_agent":
                context["preferences"] = data.get("profile", {}).get("preferences", [])

    # Include all agent results for the buddy/critic
    if agent_name in ("buddy_agent", "critic_agent"):
        context["agent_results"] = agent_results

    context["memory_context"] = state.get("memory_context", {})
    context["chat_history"] = state.get("chat_history", [])

    return context


def _build_constraints(state: WorkflowState) -> Dict[str, Any]:
    """Build constraints from state."""
    constraints: Dict[str, Any] = {}
    if state.get("budget"):
        constraints["budget"] = state["budget"]
    if state.get("style"):
        constraints["style"] = state["style"]
    if state.get("room_type"):
        constraints["room_type"] = state["room_type"]
    return constraints
