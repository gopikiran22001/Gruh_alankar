"""
Gruha Alankara — Agent Registry

Singleton registry that holds all agent instances, provides lookup
by name or capability, and exposes agent metadata for the Supervisor.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentCapability
from config.logging_config import get_logger

logger = get_logger(__name__)


class AgentRegistry:
    """
    Central registry for all agent instances.

    The Supervisor queries this registry to:
    1. Discover available agents and their capabilities
    2. Look up agents by name or task type
    3. Get agent instances for execution
    """

    _instance: Optional["AgentRegistry"] = None

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._agents: Dict[str, BaseAgent] = {}
        self._capabilities: Dict[str, AgentCapability] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        self._agents[agent.name] = agent
        self._capabilities[agent.name] = agent.get_capability()
        logger.info(
            "agent_registered",
            name=agent.name,
            task_types=agent.supported_task_types,
        )

    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def get_or_raise(self, name: str) -> BaseAgent:
        """Get an agent by name, raising if not found."""
        agent = self._agents.get(name)
        if agent is None:
            raise ValueError(f"Agent not found: {name}")
        return agent

    def find_by_task_type(self, task_type: str) -> List[BaseAgent]:
        """Find all agents that can handle a given task type."""
        return [
            agent for agent in self._agents.values()
            if agent.can_handle(task_type)
        ]

    def find_by_capability(self, capability_keyword: str) -> List[BaseAgent]:
        """Find agents whose capabilities match a keyword."""
        keyword_lower = capability_keyword.lower()
        results = []
        for name, cap in self._capabilities.items():
            if any(keyword_lower in c.lower() for c in cap.capabilities):
                results.append(self._agents[name])
        return results

    def get_all_capabilities(self) -> List[AgentCapability]:
        """Get capability descriptors for all registered agents."""
        return list(self._capabilities.values())

    def get_capabilities_summary(self) -> str:
        """
        Generate a text summary of all agents and their capabilities.
        This is injected into the Supervisor's prompt.
        """
        lines = ["Available Agents and Capabilities:\n"]
        for cap in self._capabilities.values():
            lines.append(f"Agent: {cap.agent_name}")
            lines.append(f"  Description: {cap.description}")
            lines.append(f"  Task Types: {', '.join(cap.supported_task_types)}")
            lines.append(f"  Capabilities: {', '.join(cap.capabilities)}")
            lines.append(f"  Latency: ~{cap.estimated_latency_s}s")
            if cap.requires_gpu:
                lines.append("  ⚡ Requires GPU")
            if cap.requires_internet:
                lines.append("  🌐 Requires Internet")
            lines.append("")
        return "\n".join(lines)

    @property
    def agent_names(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    @property
    def agent_count(self) -> int:
        """Number of registered agents."""
        return len(self._agents)

    def clear(self) -> None:
        """Clear all registered agents (for testing)."""
        self._agents.clear()
        self._capabilities.clear()


def initialize_agents() -> AgentRegistry:
    """
    Initialize and register all agents.
    Called during app startup.
    """
    registry = AgentRegistry()

    # Import and register all agents
    from app.agents.buddy_agent import BuddyAgent
    from app.agents.vision_agent import VisionAgent
    from app.agents.design_agent import DesignAgent
    from app.agents.furniture_agent import FurnitureAgent
    from app.agents.web_agent import WebAgent
    from app.agents.budget_agent import BudgetAgent
    from app.agents.booking_agent import BookingAgent
    from app.agents.memory_agent import MemoryAgent
    from app.agents.voice_agent import VoiceAgent
    from app.agents.critic_agent import CriticAgent
    from app.agents.supervisor_agent import SupervisorAgent
    from app.agents.image_generation_agent import ImageGenerationAgent

    agents: List[BaseAgent] = [
        BuddyAgent(),
        VisionAgent(),
        DesignAgent(),
        FurnitureAgent(),
        WebAgent(),
        BudgetAgent(),
        BookingAgent(),
        MemoryAgent(),
        VoiceAgent(),
        CriticAgent(),
        SupervisorAgent(),
        ImageGenerationAgent(),
    ]

    for agent in agents:
        registry.register(agent)

    logger.info("all_agents_initialized", count=registry.agent_count)
    return registry


# Module-level singleton
agent_registry = AgentRegistry()
