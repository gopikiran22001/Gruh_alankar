"""
Gruha Alankara — Workflow State Definition

TypedDict state schema for LangGraph workflows.
This is the shared state passed between all nodes in the graph.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from typing_extensions import TypedDict


def merge_agent_results(left: Dict[str, Dict[str, Any]], right: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Merge agent results dictionaries."""
    merged = dict(left) if left else {}
    if right:
        merged.update(right)
    return merged


class WorkflowState(TypedDict, total=False):
    """
    LangGraph state shared across all nodes in a workflow.

    This is the central data structure that flows through the
    dynamically-generated execution graph.
    """

    # ── Identifiers ──
    workflow_id: str
    user_id: str
    session_id: str
    plan_id: str

    # ── User Input ──
    user_message: str
    image_paths: List[str]
    audio_path: Optional[str]

    # ── Intent & Planning ──
    user_intent: Dict[str, Any]
    execution_plan: Dict[str, Any]

    # ── Constraints ──
    budget: Optional[float]
    style: Optional[str]
    room_type: Optional[str]
    preferences: Dict[str, Any]

    # ── Context ──
    chat_history: List[str]
    memory_context: Dict[str, Any]

    # ── Agent Results (keyed by agent_name) ──
    # Using custom merge function for concurrent updates
    agent_results: Annotated[Dict[str, Dict[str, Any]], merge_agent_results]

    # ── Current Execution ──
    current_task_id: str
    current_agent: str
    tasks_completed: List[str]
    tasks_failed: List[str]

    # ── Critic Validation ──
    critic_feedback: Dict[str, Any]
    is_validated: bool

    # ── Retry Management ──
    retry_count: int
    max_retries: int
    retry_agents: Dict[str, Dict[str, Any]]

    # ── Final Output ──
    final_response: str
    status: str  # pending, running, success, failed

    # ── Metadata ──
    errors: List[str]
    total_duration_ms: float
    total_tokens_used: int
