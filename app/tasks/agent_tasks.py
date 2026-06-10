"""
Gruha Alankara — Celery Agent Tasks

Async wrappers for long-running agent operations.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.tasks.celery_app import celery
from config.logging_config import get_logger

logger = get_logger(__name__)


@celery.task(bind=True, name="app.tasks.agent_tasks.run_workflow", max_retries=2)
def run_workflow(
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
    """Run a full autonomous workflow as a background task."""
    try:
        from app.orchestration.executor import workflow_executor

        result = asyncio.run(
            workflow_executor.run_workflow(
                user_id=user_id,
                session_id=session_id,
                message=message,
                image_paths=image_paths,
                audio_path=audio_path,
                chat_history=chat_history,
                budget=budget,
                style=style,
                room_type=room_type,
                project_id=project_id,
            )
        )
        return result

    except Exception as e:
        logger.error("celery_workflow_failed", error=str(e), user_id=user_id)
        self.retry(countdown=30, exc=e)


@celery.task(name="app.tasks.agent_tasks.run_vision_analysis", max_retries=2)
def run_vision_analysis(image_path: str, task_type: str = "full_analysis") -> Dict[str, Any]:
    """Run vision analysis as a background task."""
    from app.agents.registry import agent_registry
    from app.agents.schemas import AgentTask
    from config.constants import AgentName

    agent = agent_registry.get(AgentName.VISION)
    if not agent:
        return {"error": "Vision agent not available"}

    task = AgentTask(
        task_id="celery_vision",
        task_type=task_type,
        agent_name=AgentName.VISION,
        parameters={"image_path": image_path},
    )

    result = asyncio.run(agent.run(task))
    return result.model_dump()


@celery.task(name="app.tasks.agent_tasks.run_voice_synthesis", max_retries=1)
def run_voice_synthesis(text: str, language: str = "en") -> Dict[str, Any]:
    """Run TTS as a background task."""
    from app.agents.registry import agent_registry
    from app.agents.schemas import AgentTask
    from config.constants import AgentName

    agent = agent_registry.get(AgentName.VOICE)
    if not agent:
        return {"error": "Voice agent not available"}

    task = AgentTask(
        task_id="celery_tts",
        task_type="text_to_speech",
        agent_name=AgentName.VOICE,
        parameters={"text": text, "language": language},
    )

    result = asyncio.run(agent.run(task))
    return result.model_dump()


@celery.task(name="app.tasks.agent_tasks.run_web_scraping", max_retries=2)
def run_web_scraping(
    query: str,
    sources: Optional[List[str]] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """Run web scraping as a background task."""
    from app.agents.registry import agent_registry
    from app.agents.schemas import AgentTask
    from config.constants import AgentName, ScrapingSource

    agent = agent_registry.get(AgentName.WEB)
    if not agent:
        return {"error": "Web agent not available"}

    task = AgentTask(
        task_id="celery_web",
        task_type="scrape_products",
        agent_name=AgentName.WEB,
        parameters={
            "query": query,
            "sources": sources or ScrapingSource.ALL,
            "max_results": max_results,
        },
    )

    result = asyncio.run(agent.run(task))
    return result.model_dump()
