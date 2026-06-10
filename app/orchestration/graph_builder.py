"""
Gruha Alankara — Dynamic Graph Builder

Runtime graph generator that takes an ExecutionPlan from the Supervisor
and builds a LangGraph StateGraph dynamically. No predefined chains.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from langgraph.graph import END, StateGraph

from app.orchestration.nodes import (
    create_agent_node,
    create_critic_node,
    create_response_node,
)
from app.orchestration.workflow_state import WorkflowState
from config.logging_config import get_logger

logger = get_logger(__name__)


class DynamicGraphBuilder:
    """
    Builds LangGraph StateGraph instances dynamically from ExecutionPlans.

    The Supervisor produces an ExecutionPlan (a DAG of TaskNodes).
    This builder converts that plan into a runnable LangGraph graph with:
    - Nodes for each agent task
    - Edges respecting task dependencies
    - Conditional edges for critic validation
    - Retry loops when validation fails
    """

    def build_graph(self, plan: Dict[str, Any]) -> StateGraph:
        """
        Build a LangGraph StateGraph from an execution plan.

        Args:
            plan: ExecutionPlan dict with 'tasks' and optional 'parallel_groups'.

        Returns:
            Compiled StateGraph ready for execution.
        """
        tasks = plan.get("tasks", [])
        if not tasks:
            return self._build_simple_chat_graph()

        graph = StateGraph(WorkflowState)

        # Track node names and dependencies
        node_names: List[str] = []
        task_map: Dict[str, Dict[str, Any]] = {}

        # Add nodes for each task
        for task in tasks:
            task_id = task["task_id"]
            agent_name = task["agent_name"]
            node_name = f"{task_id}_{agent_name}"

            task_map[task_id] = {
                "node_name": node_name,
                "agent_name": agent_name,
                "task": task,
                "depends_on": task.get("depends_on", []),
            }

            # Create and add the node
            node_fn = create_agent_node(agent_name, task)
            graph.add_node(node_name, node_fn)
            node_names.append(node_name)

            logger.debug(
                "node_added",
                node=node_name,
                agent=agent_name,
                depends_on=task.get("depends_on", []),
            )

        # Build edges based on dependencies
        self._build_edges(graph, task_map, tasks)

        # Set entry point to first root task
        root_tasks = [t for t in tasks if not t.get("depends_on")]
        if root_tasks:
            first_root = f"{root_tasks[0]['task_id']}_{root_tasks[0]['agent_name']}"
            graph.set_entry_point(first_root)
        elif node_names:
            graph.set_entry_point(node_names[0])

        # Set finish point
        last_task = tasks[-1]
        last_node = f"{last_task['task_id']}_{last_task['agent_name']}"
        graph.add_edge(last_node, END)

        logger.info(
            "graph_built",
            nodes=len(node_names),
            edges=self._count_edges(task_map),
        )

        return graph.compile()

    def _build_edges(
        self,
        graph: StateGraph,
        task_map: Dict[str, Dict[str, Any]],
        tasks: List[Dict[str, Any]],
    ) -> None:
        """Build edges between nodes based on task dependencies."""
        added_edges: Set[tuple] = set()

        for task in tasks:
            task_id = task["task_id"]
            current_node = task_map[task_id]["node_name"]
            depends_on = task.get("depends_on", [])

            if depends_on:
                # Add edges from each dependency to this node
                for dep_id in depends_on:
                    if dep_id in task_map:
                        dep_node = task_map[dep_id]["node_name"]
                        edge = (dep_node, current_node)
                        if edge not in added_edges:
                            graph.add_edge(dep_node, current_node)
                            added_edges.add(edge)
            else:
                # Root task — edge from entry point is handled by set_entry_point
                # But if there are multiple root tasks, chain them
                pass

        # Handle multiple root tasks: chain them in order
        root_tasks = [t for t in tasks if not t.get("depends_on")]
        for i in range(1, len(root_tasks)):
            prev_node = f"{root_tasks[i-1]['task_id']}_{root_tasks[i-1]['agent_name']}"
            curr_node = f"{root_tasks[i]['task_id']}_{root_tasks[i]['agent_name']}"
            edge = (prev_node, curr_node)
            if edge not in added_edges:
                graph.add_edge(prev_node, curr_node)
                added_edges.add(edge)

        # Remove duplicate terminal edges — only the last node goes to END
        # (handled by the caller)

    def build_graph_with_critic(
        self,
        plan: Dict[str, Any],
        max_retries: int = 1,
    ) -> StateGraph:
        """
        Build a graph with critic validation and retry loop.

        Flow:
        [Agent Tasks] → [Critic] → {approved? → [Response] → END}
                                   {not approved? → [Replan] → [Agent Tasks]}
        """
        tasks = plan.get("tasks", [])
        if not tasks:
            return self._build_simple_chat_graph()

        graph = StateGraph(WorkflowState)

        # ── Add agent task nodes ──
        task_map: Dict[str, Dict[str, Any]] = {}
        for task in tasks:
            task_id = task["task_id"]
            agent_name = task["agent_name"]
            # Skip buddy_agent — we add it after critic
            if agent_name == "buddy_agent" and task.get("task_type") == "generate_response":
                continue

            node_name = f"{task_id}_{agent_name}"
            task_map[task_id] = {
                "node_name": node_name,
                "agent_name": agent_name,
                "task": task,
                "depends_on": task.get("depends_on", []),
            }

            node_fn = create_agent_node(agent_name, task)
            graph.add_node(node_name, node_fn)

        # ── Add critic node ──
        critic_node = create_critic_node()
        graph.add_node("critic_validate", critic_node)

        # ── Add response node ──
        response_node = create_response_node()
        graph.add_node("generate_response", response_node)

        # ── Build edges for agent tasks ──
        self._build_edges(graph, task_map, [t for t in tasks if not (
            t["agent_name"] == "buddy_agent" and t.get("task_type") == "generate_response"
        )])

        # ── Connect last agent task to critic ──
        non_buddy_tasks = [t for t in tasks if not (
            t["agent_name"] == "buddy_agent" and t.get("task_type") == "generate_response"
        )]
        if non_buddy_tasks:
            last_task = non_buddy_tasks[-1]
            last_node = f"{last_task['task_id']}_{last_task['agent_name']}"

            # Remove any existing edge from last node to END
            graph.add_edge(last_node, "critic_validate")

        # ── Conditional edge from critic ──
        def should_retry(state: WorkflowState) -> str:
            """Determine next step based on critic validation."""
            feedback = state.get("critic_feedback", {})
            is_approved = feedback.get("is_approved", True)
            overall_score = feedback.get("overall_score", 1.0)
            retry_count = state.get("retry_count", 0)
            max_r = state.get("max_retries", max_retries)

            # Only retry if score is critically low (<0.5) and below max retries
            # This prevents unnecessary retries for acceptable results
            if is_approved or overall_score >= 0.5 or retry_count >= max_r:
                return "generate_response"
            else:
                # Re-run from the first failed task
                if non_buddy_tasks:
                    first = non_buddy_tasks[0]
                    return f"{first['task_id']}_{first['agent_name']}"
                return "generate_response"

        targets = {"generate_response": "generate_response"}
        if non_buddy_tasks:
            first = non_buddy_tasks[0]
            first_node = f"{first['task_id']}_{first['agent_name']}"
            targets[first_node] = first_node

        graph.add_conditional_edges("critic_validate", should_retry, targets)

        # ── Response → END ──
        graph.add_edge("generate_response", END)

        # ── Entry point ──
        root_tasks = [t for t in non_buddy_tasks if not t.get("depends_on")]
        if root_tasks:
            first_root = f"{root_tasks[0]['task_id']}_{root_tasks[0]['agent_name']}"
            graph.set_entry_point(first_root)

        logger.info(
            "critic_graph_built",
            task_nodes=len(task_map),
            with_critic=True,
        )

        return graph.compile()

    def _build_simple_chat_graph(self) -> StateGraph:
        """Build a simple chat-only graph as ultimate fallback."""
        graph = StateGraph(WorkflowState)

        buddy_node = create_agent_node("buddy_agent", {
            "task_id": "simple_chat",
            "task_type": "chat",
        })

        graph.add_node("buddy_chat", buddy_node)
        graph.set_entry_point("buddy_chat")
        graph.add_edge("buddy_chat", END)

        return graph.compile()

    @staticmethod
    def _count_edges(task_map: Dict[str, Dict[str, Any]]) -> int:
        """Count total edges in the graph."""
        return sum(len(v["depends_on"]) for v in task_map.values())
