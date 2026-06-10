"""
Gruha Alankara — Abstract Base Agent

All agents inherit from BaseAgent, which provides:
- Standard execute/validate interface
- Execution logging
- Error handling
- Capability descriptor generation
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.agents.schemas import (
    AgentCapability,
    AgentResult,
    AgentTask,
    TaskStatusEnum,
)
from app.database.mongo import log_agent_execution
from config.logging_config import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all Gruha Alankara agents.

    Subclasses must implement:
    - execute(task) -> AgentResult
    - capabilities property

    The base class provides:
    - Standardized execution wrapper with timing and logging
    - Error handling and result wrapping
    - Capability descriptor for the Supervisor
    """

    name: str = "base_agent"
    description: str = "Base agent"
    supported_task_types: List[str] = []
    requires_gpu: bool = False
    requires_internet: bool = False
    estimated_latency_s: float = 10.0

    def __init__(self) -> None:
        self._logger = get_logger(f"agent.{self.name}")

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute a task and return a result.

        This is the core method each agent must implement.
        It receives an AgentTask with parameters and context,
        and must return an AgentResult.

        Args:
            task: The task to execute.

        Returns:
            AgentResult with status, data, and metadata.
        """
        ...

    async def run(self, task: AgentTask) -> AgentResult:
        """
        Wrapper around execute() that adds:
        - Timing
        - Logging to MongoDB
        - Error handling
        - Result normalization

        This is what the orchestration layer calls.
        """
        start_time = time.time()
        self._logger.info(
            "agent_task_started",
            task_id=task.task_id,
            task_type=task.task_type,
            agent=self.name,
        )

        try:
            result = await self.execute(task)
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms

            self._logger.info(
                "agent_task_completed",
                task_id=task.task_id,
                status=result.status.value,
                duration_ms=round(duration_ms, 1),
                confidence=result.confidence_score,
            )

            # Log to MongoDB
            self._log_execution(task, result, duration_ms)

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._logger.error(
                "agent_task_failed",
                task_id=task.task_id,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 1),
            )

            error_result = AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[str(e)],
                duration_ms=duration_ms,
            )

            self._log_execution(task, error_result, duration_ms, error=str(e))

            return error_result

    def _log_execution(
        self,
        task: AgentTask,
        result: AgentResult,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Log execution details to MongoDB agent_logs collection."""
        try:
            log_agent_execution(
                workflow_id=task.metadata.get("workflow_id", "unknown"),
                agent_name=self.name,
                task_type=task.task_type,
                input_data=task.parameters,
                output_data=result.data,
                status=result.status.value,
                duration_ms=duration_ms,
                error=error,
            )
        except Exception as log_error:
            # Don't let logging failures crash the agent
            self._logger.warning(
                "agent_log_write_failed",
                error=str(log_error),
            )

    def get_capability(self) -> AgentCapability:
        """
        Generate a capability descriptor for the Supervisor.
        The Supervisor uses this to decide which agents to invoke.
        """
        return AgentCapability(
            agent_name=self.name,
            description=self.description,
            capabilities=self._get_capabilities(),
            supported_task_types=self.supported_task_types,
            estimated_latency_s=self.estimated_latency_s,
            requires_gpu=self.requires_gpu,
            requires_internet=self.requires_internet,
        )

    def _get_capabilities(self) -> List[str]:
        """
        Return a list of human-readable capability strings.
        Override in subclasses for specific capabilities.
        """
        return [self.description]

    @staticmethod
    def generate_task_id() -> str:
        """Generate a unique task ID."""
        return str(uuid.uuid4())[:8]

    def can_handle(self, task_type: str) -> bool:
        """Check if this agent can handle a given task type."""
        return task_type in self.supported_task_types
