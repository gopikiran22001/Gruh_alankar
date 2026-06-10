"""
Gruha Alankara — Qwen2.5-VL Multimodal Client

Cloud API client for Qwen2.5-VL vision-language model.
Used for image understanding when the Vision Agent needs
LLM-level analysis beyond pure CV models.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.llm.base_client import BaseLLMClient, LLMResponse
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class QwenVLClient(BaseLLMClient):
    """
    Qwen2.5-VL multimodal API client.

    Supports:
    - Image + text inputs
    - Base64 encoded images
    - URL-referenced images
    - Multiple images per request
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
    ):
        api_key = api_key or settings.qwen.API_KEY
        api_url = api_url or settings.qwen.API_URL
        model = model or settings.qwen.VL_MODEL

        super().__init__(
            api_key=api_key,
            api_url=api_url,
            model=model,
            timeout=timeout,
        )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
            timeout=self.timeout,
        )

    def _call_api(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call Qwen2.5-VL API with multimodal messages."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            choice = response.choices[0]
            message = choice.message

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=message.content or "",
                model=self.model,
                usage=usage,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(
                "qwen_vl_api_error",
                model=self.model,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Analyze a local image with a text prompt.

        Args:
            image_path: Path to the image file.
            prompt: Analysis instruction.
            system_prompt: Optional system instructions.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens.

        Returns:
            LLMResponse with the analysis.
        """
        base64_image = self._encode_image(image_path)
        mime_type = self._get_mime_type(image_path)

        messages: List[Dict[str, Any]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}",
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        })

        return self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def analyze_image_url(
        self,
        image_url: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Analyze an image from a URL."""
        messages: List[Dict[str, Any]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        })

        return self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Read and base64-encode a local image file."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _get_mime_type(image_path: str) -> str:
        """Determine MIME type from file extension."""
        ext = Path(image_path).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mime_map.get(ext, "image/jpeg")
