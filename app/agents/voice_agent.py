"""
Gruha Alankara — Voice Agent

Speech-to-text using Faster Whisper and text-to-speech using gTTS.
Supports multilingual input/output.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from app.database.mongo import insert_one
from config.constants import AgentName, MongoCollection
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class VoiceAgent(BaseAgent):
    """
    Voice processing agent.

    Models:
    - Faster Whisper (large-v3): Speech-to-text
    - gTTS: Text-to-speech with multilingual support (simple, compatible)

    Models are loaded lazily on first use to save memory.
    """

    name = AgentName.VOICE
    description = "Converts speech to text and text to speech with multilingual support"
    supported_task_types = [
        "speech_to_text",
        "text_to_speech",
    ]
    requires_gpu = True
    estimated_latency_s = 10.0

    def __init__(self) -> None:
        super().__init__()
        self._whisper_model = None
        self._tts_model = None
        self._output_dir = Path(settings.storage.UPLOAD_DIR) / "voice_output"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _get_capabilities(self) -> List[str]:
        return [
            "Transcribe speech to text (Hindi, English, Kannada, and more)",
            "Convert text to natural-sounding speech",
            "Multilingual voice support",
            "Audio file processing",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "speech_to_text": self._speech_to_text,
            "text_to_speech": self._text_to_speech,
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

    async def _speech_to_text(self, task: AgentTask) -> AgentResult:
        """Transcribe audio using Faster Whisper."""
        audio_path = task.parameters.get("audio_path", "")
        language = task.parameters.get("language")  # None = auto-detect

        if not audio_path or not Path(audio_path).exists():
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Audio file not found"],
            )

        try:
            self._load_whisper()

            segments, info = self._whisper_model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                ),
            )

            # Collect all segments
            transcript_parts = []
            segment_list = []
            for segment in segments:
                transcript_parts.append(segment.text)
                segment_list.append({
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "confidence": round(segment.avg_logprob, 3) if hasattr(segment, "avg_logprob") else None,
                })

            full_transcript = " ".join(transcript_parts).strip()

            # Log voice interaction
            try:
                insert_one(MongoCollection.VOICE_LOGS, {
                    "type": "speech_to_text",
                    "audio_path": audio_path,
                    "detected_language": info.language,
                    "language_probability": round(info.language_probability, 3),
                    "duration_s": round(info.duration, 2),
                    "transcript_length": len(full_transcript),
                })
            except Exception:
                pass

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.SUCCESS,
                data={
                    "transcript": full_transcript,
                    "segments": segment_list,
                    "detected_language": info.language,
                    "language_probability": round(info.language_probability, 3),
                    "duration_s": round(info.duration, 2),
                },
                confidence_score=info.language_probability,
            )

        except Exception as e:
            logger.error("speech_to_text_failed", error=str(e))
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Transcription failed: {str(e)}"],
            )

    async def _text_to_speech(self, task: AgentTask) -> AgentResult:
        """Convert text to speech using gTTS."""
        text = task.parameters.get("text", "")
        language = task.parameters.get("language", "en")
        speaker_wav = task.parameters.get("speaker_wav")  # Reference audio for voice cloning

        if not text:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Text is required for speech synthesis"],
            )

        try:
            self._load_tts()

            output_filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"  # gTTS outputs MP3
            output_path = str(self._output_dir / output_filename)

            # Generate speech using gTTS (simpler, no voice cloning)
            tts = self._tts_model(text=text, lang=language[:2])  # gTTS uses 2-letter codes
            tts.save(output_path)

            # Log
            try:
                insert_one(MongoCollection.VOICE_LOGS, {
                    "type": "text_to_speech",
                    "text_length": len(text),
                    "language": language,
                    "output_path": output_path,
                })
            except Exception:
                pass

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.SUCCESS,
                data={
                    "audio_path": output_path,
                    "filename": output_filename,
                    "language": language,
                    "text_length": len(text),
                },
            )

        except Exception as e:
            logger.error("text_to_speech_failed", error=str(e))
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Speech synthesis failed: {str(e)}"],
            )

    def _load_whisper(self) -> None:
        """Lazily load Faster Whisper model."""
        if self._whisper_model is not None:
            return

        from faster_whisper import WhisperModel

        model_size = settings.voice.WHISPER_MODEL_SIZE
        logger.info("loading_whisper_model", model_size=model_size)

        self._whisper_model = WhisperModel(
            model_size,
            device="cuda" if self._check_cuda() else "cpu",
            compute_type="float16" if self._check_cuda() else "int8",
        )
        logger.info("whisper_model_loaded")

    def _load_tts(self) -> None:
        """Lazily load TTS model (using gTTS for Python 3.13+ compatibility)."""
        if self._tts_model is not None:
            return

        # Use gTTS for compatibility with Python 3.13+
        from gtts import gTTS
        
        logger.info("loading_gtts_model")
        self._tts_model = gTTS  # Store the class, not instance
        logger.info("gtts_model_loaded")

    @staticmethod
    def _check_cuda() -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
