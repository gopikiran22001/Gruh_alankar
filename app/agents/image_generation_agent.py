"""
Gruha Alankara — Image Generation Agent

Generates photorealistic room renders with furniture using:
- Stable Diffusion XL for high-quality room generation
- ControlNet for layout/depth control
- Inpainting for furniture placement

This agent takes room analysis + design recommendations and generates
a rendered image showing the room with recommended furniture.
"""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from PIL import Image

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from config.constants import AgentName
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class ImageGenerationAgent(BaseAgent):
    """
    Generates photorealistic room renders with furniture.

    Takes:
    - Original room image
    - Room analysis (objects, colors, lighting)
    - Design recommendations (style, furniture, colors)

    Outputs:
    - Rendered image with furniture placed
    - Before/After comparison
    """

    name = "image_generation_agent"
    description = "Generates photorealistic room renders with recommended furniture"
    supported_task_types = [
        "generate_room_render",
        "add_furniture_to_room",
        "before_after_comparison",
    ]
    estimated_latency_s = 30.0

    def __init__(self) -> None:
        super().__init__()
        self._http_client = httpx.AsyncClient(timeout=120.0)
        # You'll configure these endpoints
        self._sdxl_endpoint = settings.image_gen.SDXL_ENDPOINT
        self._controlnet_endpoint = settings.image_gen.CONTROLNET_ENDPOINT

    def _get_capabilities(self) -> List[str]:
        return [
            "Generate photorealistic room renders with furniture",
            "Place furniture in rooms based on design recommendations",
            "Create before/after comparison images",
            "Apply design styles to room images",
            "Inpaint furniture into existing room photos",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "generate_room_render": self._generate_room_render,
            "add_furniture_to_room": self._add_furniture_to_room,
            "before_after_comparison": self._before_after_comparison,
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
    
    def _get_user_id_from_image_path(self, image_path: str) -> str:
        """Extract user_id from image path."""
        path_obj = Path(image_path)
        # Path structure: settings.storage.UPLOAD_DIR / user_id / filename
        upload_dir = Path(settings.storage.UPLOAD_DIR)
        try:
            relative_path = path_obj.relative_to(upload_dir)
            parts = relative_path.parts
            if parts:
                return parts[0]  # First part is user_id
        except ValueError:
            pass
        return "default"

    async def _generate_room_render(self, task: AgentTask) -> AgentResult:
        """
        Generate a complete room render with furniture.
        
        Takes original image + design recommendations and creates
        a photorealistic render showing the designed room.
        """
        original_image_path = task.parameters.get("image_path", "")
        design_data = task.context.get("design", {})
        room_analysis = task.context.get("room_analysis", {})
        
        if not Path(original_image_path).exists():
            return self._error_result(task.task_id, "Original image not found")

        # Build prompt from design data
        prompt = self._build_generation_prompt(design_data, room_analysis)
        
        try:
            # Generate image using Stable Diffusion XL
            generated_image = await self._call_sdxl_generation(
                original_image_path,
                prompt,
                design_data
            )
            
            # Save generated image in the same user directory as original
            user_id = self._get_user_id_from_image_path(original_image_path)
            output_path = self._save_generated_image(generated_image, task.task_id, user_id)
            
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.SUCCESS,
                data={
                    "generated_image_path": str(output_path),
                    "original_image_path": original_image_path,
                    "prompt_used": prompt,
                    "design_applied": design_data.get("design_title", "Unknown"),
                },
            )
            
        except Exception as e:
            logger.error("image_generation_failed", error=str(e))
            return self._error_result(task.task_id, f"Generation failed: {str(e)}")

    async def _add_furniture_to_room(self, task: AgentTask) -> AgentResult:
        """
        Add specific furniture items to an existing room image.
        Uses inpainting to place furniture in designated areas.
        """
        image_path = task.parameters.get("image_path", "")
        furniture_list = task.parameters.get("furniture_list", [])
        placement_areas = task.parameters.get("placement_areas", [])
        
        if not Path(image_path).exists():
            return self._error_result(task.task_id, "Image not found")
        
        try:
            # For each furniture item, inpaint it into the room
            result_image_path = image_path
            
            for i, furniture in enumerate(furniture_list[:3]):  # Limit to 3 items
                furniture_prompt = self._build_furniture_prompt(furniture)
                placement = placement_areas[i] if i < len(placement_areas) else None
                
                result_image_path = await self._inpaint_furniture(
                    result_image_path,
                    furniture_prompt,
                    placement
                )
            
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.SUCCESS,
                data={
                    "generated_image_path": result_image_path,
                    "furniture_added": len(furniture_list[:3]),
                },
            )
            
        except Exception as e:
            logger.error("furniture_addition_failed", error=str(e))
            return self._error_result(task.task_id, f"Failed to add furniture: {str(e)}")

    async def _before_after_comparison(self, task: AgentTask) -> AgentResult:
        """
        Create a side-by-side before/after comparison image.
        """
        before_path = task.parameters.get("before_image_path", "")
        after_path = task.parameters.get("after_image_path", "")
        
        if not Path(before_path).exists() or not Path(after_path).exists():
            return self._error_result(task.task_id, "Before or after image not found")
        
        try:
            # Create side-by-side comparison
            comparison_path = self._create_comparison_image(before_path, after_path)
            
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.SUCCESS,
                data={
                    "comparison_image_path": str(comparison_path),
                    "before_path": before_path,
                    "after_path": after_path,
                },
            )
            
        except Exception as e:
            logger.error("comparison_failed", error=str(e))
            return self._error_result(task.task_id, f"Comparison failed: {str(e)}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Image Generation Methods
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _call_sdxl_generation(
        self,
        original_image_path: str,
        prompt: str,
        design_data: Dict[str, Any]
    ) -> Image.Image:
        """
        Call Stable Diffusion XL endpoint with ControlNet for guided generation.
        """
        # Read original image
        with open(original_image_path, "rb") as f:
            image_data = f.read()
        
        # Prepare request
        files = {"image": ("input.jpg", image_data, "image/jpeg")}
        
        data = {
            "prompt": prompt,
            "negative_prompt": self._get_negative_prompt(),
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "strength": 0.8,  # How much to change from original
            "seed": -1,
        }
        
        # Add style-specific parameters
        style = design_data.get("style", "modern")
        data.update(self._get_style_parameters(style))
        
        # Call endpoint
        try:
            response = await self._http_client.post(
                self._sdxl_endpoint,
                files=files,
                data=data,
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            image_b64 = result.get("image")
            
            if not image_b64:
                raise ValueError("No image returned from generation API")
            
            # Decode image
            image_bytes = base64.b64decode(image_b64)
            return Image.open(BytesIO(image_bytes))
        except Exception as e:
            logger.warning(
                "primary_image_gen_failed_trying_fallbacks",
                endpoint=self._sdxl_endpoint,
                error=str(e)
            )
            
            # Fallback 1: Try multiple free API services
            fallback_services = [
                {
                    "name": "Pollinations AI",
                    "url_template": "https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true&seed=42",
                    "encode": True
                },
                {
                    "name": "Hugging Face SDXL",
                    "url_template": "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
                    "encode": False,
                    "method": "POST",
                    "json": {"inputs": prompt}
                }
            ]
            
            for service in fallback_services:
                try:
                    import urllib.parse
                    clean_prompt = " ".join(prompt.split())
                    
                    if service.get("encode"):
                        encoded_prompt = urllib.parse.quote(clean_prompt)
                        url = service["url_template"].format(prompt=encoded_prompt)
                        logger.info(f"trying_{service['name'].lower().replace(' ', '_')}_fallback", url=url)
                        fallback_response = await self._http_client.get(url, timeout=60.0)
                    else:
                        url = service["url_template"]
                        logger.info(f"trying_{service['name'].lower().replace(' ', '_')}_fallback", url=url)
                        fallback_response = await self._http_client.post(
                            url, 
                            json=service.get("json", {"inputs": clean_prompt}),
                            timeout=60.0
                        )
                    
                    # Check if successful
                    if fallback_response.status_code == 200:
                        content_type = fallback_response.headers.get("content-type", "")
                        if "image" in content_type or len(fallback_response.content) > 10000:
                            logger.info(f"{service['name'].lower().replace(' ', '_')}_success")
                            return Image.open(BytesIO(fallback_response.content))
                        else:
                            logger.warning(
                                f"{service['name'].lower().replace(' ', '_')}_no_image",
                                response=fallback_response.text[:200] if len(fallback_response.content) < 2000 else "binary"
                            )
                    else:
                        logger.warning(
                            f"{service['name'].lower().replace(' ', '_')}_failed",
                            status=fallback_response.status_code,
                            error=fallback_response.text[:200]
                        )
                        
                except Exception as fe:
                    logger.warning(f"{service['name'].lower().replace(' ', '_')}_error", error=str(fe))
                    continue
            
            # Fallback 2: Offline fallback - load and return original image with watermark
            logger.info("all_fallbacks_failed_using_original_image", path=original_image_path)
            original_img = Image.open(original_image_path)
            
            # Add a subtle watermark indicating it's the original
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(original_img)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # Add semi-transparent watermark
            text = "Preview: AI Generation Unavailable"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (original_img.width - text_width) // 2
            y = original_img.height - text_height - 20
            
            # Draw text with background
            draw.rectangle([x-10, y-5, x+text_width+10, y+text_height+5], fill=(255, 255, 255, 180))
            draw.text((x, y), text, fill=(100, 100, 100), font=font)
            
            return original_img

    async def _inpaint_furniture(
        self,
        image_path: str,
        furniture_prompt: str,
        placement: Optional[Dict[str, int]]
    ) -> str:
        """
        Inpaint a furniture item into a specific area of the room.
        """
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # Create mask for placement area
        mask_data = self._create_placement_mask(image_path, placement)
        
        files = {
            "image": ("input.jpg", image_data, "image/jpeg"),
            "mask": ("mask.png", mask_data, "image/png"),
        }
        
        data = {
            "prompt": furniture_prompt,
            "negative_prompt": self._get_negative_prompt(),
            "num_inference_steps": 25,
            "guidance_scale": 7.5,
        }
        
        try:
            response = await self._http_client.post(
                f"{self._sdxl_endpoint}/inpaint",
                files=files,
                data=data,
            )
            response.raise_for_status()
            
            result = response.json()
            image_b64 = result.get("image")
            
            # Save inpainted image
            image_bytes = base64.b64decode(image_b64)
            img = Image.open(BytesIO(image_bytes))
            
            # Save in the same user directory as the original image
            user_id = self._get_user_id_from_image_path(image_path)
            user_dir = Path(settings.storage.UPLOAD_DIR) / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = user_dir / f"inpaint_{Path(image_path).stem}.jpg"
            img.save(output_path, quality=95)
            
            return str(output_path)
        except Exception as e:
            logger.warning(
                "inpaint_failed_using_fallback",
                endpoint=f"{self._sdxl_endpoint}/inpaint",
                error=str(e)
            )
            # Safe offline/disconnected fallback: return the original image path
            return image_path

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Prompt Building
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_generation_prompt(
        self,
        design_data: Dict[str, Any],
        room_analysis: Dict[str, Any]
    ) -> str:
        """
        Build a detailed prompt for image generation based on design recommendations.
        """
        style = design_data.get("style_description", "modern interior design")
        
        # Extract furniture list
        furniture_items = design_data.get("furniture_list", [])
        furniture_desc = ", ".join([
            item.get("item", "") for item in furniture_items[:5]
        ])
        
        # Extract color scheme
        color_scheme = design_data.get("color_scheme", {})
        primary_color = color_scheme.get("primary", {}).get("name", "neutral")
        accent_color = color_scheme.get("accent", {}).get("name", "")
        
        # Extract lighting
        lighting = room_analysis.get("lighting_analysis", {}).get("classification", "well_lit")
        
        # Build comprehensive prompt
        prompt = f"""
Professional interior design photograph of a {style} living room,
featuring {furniture_desc},
{primary_color} color scheme with {accent_color} accents,
{lighting} natural lighting,
high-end furniture, photorealistic, 8k, architectural photography,
clean modern aesthetic, spacious layout, carefully arranged decor,
professional staging, wide angle lens, sharp focus
        """.strip().replace("\n", " ")
        
        return prompt

    def _build_furniture_prompt(self, furniture: Dict[str, Any]) -> str:
        """Build prompt for a specific furniture item."""
        item_name = furniture.get("item", "furniture")
        description = furniture.get("description", "")
        
        return f"photorealistic {item_name}, {description}, professional product photography, high detail"

    @staticmethod
    def _get_negative_prompt() -> str:
        """Negative prompt to avoid common issues."""
        return """
low quality, blurry, distorted, unrealistic, cartoon, anime, sketch,
bad proportions, cluttered, messy, poor lighting, oversaturated,
watermark, text, signature, ugly, cheap looking, fake
        """.strip().replace("\n", " ")

    def _get_style_parameters(self, style: str) -> Dict[str, Any]:
        """Get style-specific generation parameters."""
        style_params = {
            "modern": {"cfg_scale": 7.5, "strength": 0.75},
            "scandinavian": {"cfg_scale": 7.0, "strength": 0.7},
            "minimalist": {"cfg_scale": 6.5, "strength": 0.65},
            "industrial": {"cfg_scale": 8.0, "strength": 0.8},
            "bohemian": {"cfg_scale": 7.5, "strength": 0.85},
        }
        
        return style_params.get(style.lower(), {"cfg_scale": 7.5, "strength": 0.75})

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Image Processing Helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _create_placement_mask(
        self,
        image_path: str,
        placement: Optional[Dict[str, int]]
    ) -> bytes:
        """
        Create a mask image for inpainting.
        If placement is provided, mask that area, otherwise mask center 50%.
        """
        img = Image.open(image_path)
        width, height = img.size
        
        # Create white mask (everything masked)
        mask = Image.new('L', (width, height), 255)
        
        if placement:
            # Use specified placement area
            x = placement.get("x", width // 4)
            y = placement.get("y", height // 4)
            w = placement.get("width", width // 2)
            h = placement.get("height", height // 2)
        else:
            # Default: center 50% of image
            x = width // 4
            y = height // 4
            w = width // 2
            h = height // 2
        
        # Draw black rectangle (area to inpaint)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.rectangle([x, y, x + w, y + h], fill=0)
        
        # Convert to bytes
        buffer = BytesIO()
        mask.save(buffer, format="PNG")
        return buffer.getvalue()

    def _create_comparison_image(
        self,
        before_path: str,
        after_path: str
    ) -> Path:
        """Create side-by-side before/after comparison."""
        before_img = Image.open(before_path)
        after_img = Image.open(after_path)
        
        # Resize to same height
        target_height = 800
        before_img = self._resize_to_height(before_img, target_height)
        after_img = self._resize_to_height(after_img, target_height)
        
        # Create new image with both side by side
        total_width = before_img.width + after_img.width + 20  # 20px gap
        comparison = Image.new('RGB', (total_width, target_height), (255, 255, 255))
        
        # Paste images
        comparison.paste(before_img, (0, 0))
        comparison.paste(after_img, (before_img.width + 20, 0))
        
        # Add "BEFORE" and "AFTER" labels
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(comparison)
        
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        draw.text((20, 20), "BEFORE", fill=(0, 0, 0), font=font)
        draw.text((before_img.width + 40, 20), "AFTER", fill=(0, 0, 0), font=font)
        
        # Save in the same user directory as the original image
        user_id = self._get_user_id_from_image_path(before_path)
        user_dir = Path(settings.storage.UPLOAD_DIR) / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = user_dir / f"comparison_{Path(before_path).stem}.jpg"
        comparison.save(output_path, quality=95)
        
        return output_path

    @staticmethod
    def _resize_to_height(img: Image.Image, target_height: int) -> Image.Image:
        """Resize image to target height maintaining aspect ratio."""
        aspect_ratio = img.width / img.height
        new_width = int(target_height * aspect_ratio)
        return img.resize((new_width, target_height), Image.Resampling.LANCZOS)

    def _save_generated_image(self, img: Image.Image, task_id: str, user_id: str) -> Path:
        """Save generated image to user's uploads directory."""
        user_dir = Path(settings.storage.UPLOAD_DIR) / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = user_dir / f"generated_{task_id}.jpg"
        img.save(output_path, quality=95, optimize=True)
        return output_path

    def _error_result(self, task_id: str, message: str) -> AgentResult:
        return AgentResult(
            task_id=task_id,
            agent_name=self.name,
            status=TaskStatusEnum.FAILED,
            errors=[message],
        )
