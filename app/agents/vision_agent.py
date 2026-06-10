"""
Gruha Alankara — Vision Agent

Analyzes room images using external model-serving endpoints
for Florence-2, YOLOv11, and SAM2, plus local OpenCV analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import httpx
import numpy as np
from PIL import Image

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from config.constants import AgentName
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class VisionAgent(BaseAgent):
    """
    Room analysis agent using vision models served via external endpoints.

    Models:
    - Florence-2: Dense captioning, room description
    - YOLOv11: Object/furniture detection
    - SAM2: Semantic segmentation

    Also uses local OpenCV for color and lighting analysis.
    """

    name = AgentName.VISION
    description = "Analyzes room images for objects, colors, lighting, and spatial layout"
    supported_task_types = [
        "analyze_room",
        "detect_objects",
        "segment_room",
        "extract_colors",
        "analyze_lighting",
        "full_analysis",
    ]
    requires_gpu = False  # Models are served externally
    estimated_latency_s = 15.0

    def __init__(self) -> None:
        super().__init__()
        self._florence_url = settings.vision.FLORENCE2_ENDPOINT
        self._yolo_url = settings.vision.YOLOV11_ENDPOINT
        self._sam2_url = settings.vision.SAM2_ENDPOINT
        self._http_client = httpx.AsyncClient(timeout=60.0)

    def _get_capabilities(self) -> List[str]:
        return [
            "Room image analysis and description",
            "Object and furniture detection with bounding boxes",
            "Semantic segmentation of room areas",
            "Dominant color extraction",
            "Lighting condition analysis",
            "Room dimension estimation",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        """Route to the appropriate vision task."""
        handlers = {
            "analyze_room": self._analyze_room,
            "detect_objects": self._detect_objects,
            "segment_room": self._segment_room,
            "extract_colors": self._extract_colors,
            "analyze_lighting": self._analyze_lighting,
            "full_analysis": self._full_analysis,
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

    async def _full_analysis(self, task: AgentTask) -> AgentResult:
        """Run all analysis tasks on a room image."""
        image_path = task.parameters.get("image_path", "")
        if not self._validate_image(image_path):
            return self._error_result(task.task_id, "Invalid or missing image file")

        results: Dict[str, Any] = {}

        # Run Florence-2 for room description
        try:
            caption_result = await self._call_florence2(image_path, "dense_captioning")
            results["room_description"] = caption_result
        except Exception as e:
            logger.warning("florence2_failed", error=str(e))
            results["room_description"] = {"error": str(e)}

        # Run YOLO for object detection
        try:
            detection_result = await self._call_yolo(image_path)
            results["detected_objects"] = detection_result
        except Exception as e:
            logger.warning("yolo_failed", error=str(e))
            results["detected_objects"] = {"error": str(e)}

        # Run local color analysis
        try:
            colors = self._local_extract_colors(image_path)
            results["color_analysis"] = colors
        except Exception as e:
            logger.warning("color_analysis_failed", error=str(e))
            results["color_analysis"] = {"error": str(e)}

        # Run local lighting analysis
        try:
            lighting = self._local_analyze_lighting(image_path)
            results["lighting_analysis"] = lighting
        except Exception as e:
            logger.warning("lighting_analysis_failed", error=str(e))
            results["lighting_analysis"] = {"error": str(e)}

        # Run SAM2 segmentation
        try:
            segmentation = await self._call_sam2(image_path)
            results["segmentation"] = segmentation
        except Exception as e:
            logger.warning("sam2_failed", error=str(e))
            results["segmentation"] = {"error": str(e)}

        # Determine confidence based on successful analyses
        successful = sum(1 for v in results.values() if "error" not in v)
        confidence = successful / len(results)

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data=results,
            confidence_score=confidence,
        )

    async def _analyze_room(self, task: AgentTask) -> AgentResult:
        """Analyze room using Florence-2 for dense captioning."""
        image_path = task.parameters.get("image_path", "")
        if not self._validate_image(image_path):
            return self._error_result(task.task_id, "Invalid or missing image file")

        result = await self._call_florence2(image_path, "dense_captioning")

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"room_description": result},
        )

    async def _detect_objects(self, task: AgentTask) -> AgentResult:
        """Detect objects using YOLOv11."""
        image_path = task.parameters.get("image_path", "")
        if not self._validate_image(image_path):
            return self._error_result(task.task_id, "Invalid or missing image file")

        result = await self._call_yolo(image_path)

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"detected_objects": result},
        )

    async def _segment_room(self, task: AgentTask) -> AgentResult:
        """Segment room using SAM2."""
        image_path = task.parameters.get("image_path", "")
        if not self._validate_image(image_path):
            return self._error_result(task.task_id, "Invalid or missing image file")

        result = await self._call_sam2(image_path)

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"segmentation": result},
        )

    async def _extract_colors(self, task: AgentTask) -> AgentResult:
        """Extract dominant colors from the image."""
        image_path = task.parameters.get("image_path", "")
        if not self._validate_image(image_path):
            return self._error_result(task.task_id, "Invalid or missing image file")

        colors = self._local_extract_colors(image_path)

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"color_analysis": colors},
        )

    async def _analyze_lighting(self, task: AgentTask) -> AgentResult:
        """Analyze lighting conditions."""
        image_path = task.parameters.get("image_path", "")
        if not self._validate_image(image_path):
            return self._error_result(task.task_id, "Invalid or missing image file")

        lighting = self._local_analyze_lighting(image_path)

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={"lighting_analysis": lighting},
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Model Endpoint Callers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _call_florence2(self, image_path: str, task_type: str) -> Dict[str, Any]:
        """Call Florence-2 model serving endpoint."""
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = await self._http_client.post(
            self._florence_url,
            files={"image": ("image.jpg", image_data)},
            data={"task": task_type},
        )
        response.raise_for_status()
        return response.json()

    async def _call_yolo(self, image_path: str) -> Dict[str, Any]:
        """Call YOLOv11 model serving endpoint."""
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = await self._http_client.post(
            self._yolo_url,
            files={"image": ("image.jpg", image_data)},
            data={"confidence_threshold": "0.5"},
        )
        response.raise_for_status()
        return response.json()

    async def _call_sam2(self, image_path: str) -> Dict[str, Any]:
        """Call SAM2 model serving endpoint."""
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = await self._http_client.post(
            self._sam2_url,
            files={"image": ("image.jpg", image_data)},
        )
        response.raise_for_status()
        return response.json()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Local OpenCV Analysis
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _local_extract_colors(self, image_path: str, k: int = 5) -> Dict[str, Any]:
        """
        Extract dominant colors using K-means clustering.
        Returns hex codes, RGB values, and percentage of image.
        """
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize for speed
        image_small = cv2.resize(image, (200, 200))
        pixels = image_small.reshape(-1, 3).astype(np.float32)

        # K-means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        # Calculate percentages
        label_counts = np.bincount(labels.flatten())
        total = labels.shape[0]
        percentages = (label_counts / total * 100).tolist()

        # Build color list
        colors = []
        for i, center in enumerate(centers):
            r, g, b = int(center[0]), int(center[1]), int(center[2])
            hex_code = f"#{r:02x}{g:02x}{b:02x}"
            colors.append({
                "hex": hex_code,
                "rgb": [r, g, b],
                "percentage": round(percentages[i], 1),
            })

        # Sort by percentage descending
        colors.sort(key=lambda x: x["percentage"], reverse=True)

        return {
            "dominant_colors": colors,
            "color_count": k,
        }

    def _local_analyze_lighting(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze lighting conditions of the room.
        Returns brightness, contrast, and lighting classification.
        """
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Brightness (mean pixel value)
        brightness = float(np.mean(gray))

        # Contrast (standard deviation)
        contrast = float(np.std(gray))

        # Histogram analysis
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        total_pixels = gray.shape[0] * gray.shape[1]

        dark_ratio = float(np.sum(hist[:85]) / total_pixels)
        mid_ratio = float(np.sum(hist[85:170]) / total_pixels)
        bright_ratio = float(np.sum(hist[170:]) / total_pixels)

        # Classify lighting
        if brightness < 80:
            classification = "dark"
        elif brightness < 130:
            classification = "moderate"
        elif brightness < 180:
            classification = "well_lit"
        else:
            classification = "bright"

        # Check for natural light indicators
        has_high_contrast = contrast > 60

        return {
            "brightness": round(brightness, 1),
            "contrast": round(contrast, 1),
            "classification": classification,
            "dark_ratio": round(dark_ratio, 3),
            "mid_ratio": round(mid_ratio, 3),
            "bright_ratio": round(bright_ratio, 3),
            "high_contrast": has_high_contrast,
            "recommendation": self._lighting_recommendation(classification),
        }

    @staticmethod
    def _lighting_recommendation(classification: str) -> str:
        """Generate lighting improvement recommendation."""
        recommendations = {
            "dark": "Consider adding ambient lighting, floor lamps, or LED strip lighting to brighten the space.",
            "moderate": "Good natural lighting base. Accent lighting can enhance specific areas.",
            "well_lit": "Excellent lighting. Focus on layered lighting for ambiance.",
            "bright": "Very bright space. Consider window treatments to control light and reduce glare.",
        }
        return recommendations.get(classification, "")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _validate_image(image_path: str) -> bool:
        """Validate that the image file exists and is readable."""
        if not image_path:
            return False
        path = Path(image_path)
        return path.exists() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    def _error_result(self, task_id: str, message: str) -> AgentResult:
        return AgentResult(
            task_id=task_id,
            agent_name=self.name,
            status=TaskStatusEnum.FAILED,
            errors=[message],
        )
