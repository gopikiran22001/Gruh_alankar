"""
Gruha Alankara — Model Preloader

Loads embedding and voice models before application startup
to avoid cold start latency on first request.
"""

from dotenv import load_dotenv
load_dotenv()

from config.logging_config import get_logger

logger = get_logger(__name__)


def preload_embedding_model():
    """Preload BGE-M3 embedding model."""
    try:
        from app.llm.embedding_client import embedding_client
        logger.info("preloading_embedding_model")
        embedding_client._load_model()
        logger.info("embedding_model_preloaded", dimension=embedding_client.dimension)
    except Exception as e:
        logger.warning("embedding_model_preload_failed", error=str(e))


def preload_voice_models():
    """Preload Whisper and TTS models."""
    try:
        from app.agents.voice_agent import VoiceAgent
        logger.info("preloading_voice_models")
        agent = VoiceAgent()
        agent._load_whisper()
        agent._load_tts()
        logger.info("voice_models_preloaded")
    except Exception as e:
        logger.warning("voice_models_preload_failed", error=str(e))


def preload_all_models():
    """Preload all required models."""
    logger.info("starting_model_preload")
    preload_embedding_model()
    preload_voice_models()
    logger.info("model_preload_complete")


if __name__ == "__main__":
    preload_all_models()
