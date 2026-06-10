"""
Gruha Alankara — Design Studio API

Complete workflow endpoint for design studio:
- Upload room image
- Analyze with vision
- Generate design recommendations  
- Create photorealistic render with furniture
- Return all results including generated image
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import uuid
import asyncio

from flask_jwt_extended import jwt_required, get_jwt_identity
from app.agents.registry import agent_registry
from app.agents.schemas import AgentTask
from config.constants import AgentName
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

design_studio_bp = Blueprint("design_studio", __name__, url_prefix="/api/design-studio")


@design_studio_bp.route("/analyze-and-design", methods=["POST"])
@jwt_required()
async def analyze_and_design():
    """
    Complete design studio workflow:
    1. Upload room image
    2. Vision analysis
    3. Design recommendations
    4. Generate AI render with furniture
    5. Return all results with image URLs
    
    Request (multipart/form-data):
        image: File (required)
        style: str (optional, e.g., "modern", "luxury")
        budget: float (optional)
        room_type: str (optional, e.g., "living_room")
        generate_render: bool (optional, default: true)
    
    Response:
    {
        "status": "success",
        "workflow_id": "...",
        "original_image_url": "/api/uploads/...",
        "generated_image_url": "/api/uploads/...",
        "comparison_image_url": "/api/uploads/...",
        "room_analysis": {...},
        "design_recommendations": {...},
        "summary": "..."
    }
    """
    try:
        user_id = get_jwt_identity()
        
        # Get uploaded image
        if "image" not in request.files:
            return jsonify({
                "status": "error",
                "message": "Image file is required"
            }), 400
        
        image_file = request.files["image"]
        if not image_file.filename:
            return jsonify({
                "status": "error", 
                "message": "No image file provided"
            }), 400
        
        # Save uploaded image
        upload_dir = Path(settings.storage.UPLOAD_DIR) / user_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        ext = Path(image_file.filename).suffix or ".jpg"
        image_filename = f"room_{uuid.uuid4().hex[:8]}{ext}"
        image_path = str(upload_dir / image_filename)
        image_file.save(image_path)
        
        # Get parameters
        style = request.form.get("style", "modern")
        budget = request.form.get("budget", type=float)
        room_type = request.form.get("room_type", "living room")
        generate_render = request.form.get("generate_render", "true").lower() == "true"
        
        workflow_id = f"design_{uuid.uuid4().hex[:8]}"
        
        logger.info(
            "design_studio_workflow_started",
            workflow_id=workflow_id,
            user_id=user_id,
            style=style,
            generate_render=generate_render,
        )
        
        result = {
            "status": "success",
            "workflow_id": workflow_id,
            "original_image_url": f"/api/uploads/{user_id}/{image_filename}",
            "original_image_path": image_path,
            "room_analysis": {},
            "design_recommendations": {},
            "generated_image_url": None,
            "comparison_image_url": None,
            "errors": [],
        }
        
        # Step 1: Vision Analysis
        vision_agent = agent_registry.get(AgentName.VISION)
        if vision_agent:
            try:
                vision_task = AgentTask(
                    task_id=f"{workflow_id}_vision",
                    task_type="full_analysis",
                    agent_name=AgentName.VISION,
                    parameters={"image_path": image_path},
                )
                
                vision_result = await vision_agent.run(vision_task)
                
                if vision_result.is_success:
                    result["room_analysis"] = vision_result.data
                    logger.info("vision_analysis_complete", workflow_id=workflow_id)
                else:
                    result["errors"].append("Vision analysis failed")
                    
            except Exception as e:
                logger.error("vision_analysis_error", error=str(e))
                result["errors"].append(f"Vision error: {str(e)}")
        
        # Step 2: Design Recommendations
        design_agent = agent_registry.get(AgentName.DESIGN)
        if design_agent:
            try:
                design_task = AgentTask(
                    task_id=f"{workflow_id}_design",
                    task_type="generate_design",
                    agent_name=AgentName.DESIGN,
                    parameters={
                        "style": style,
                        "room_type": room_type,
                    },
                    context={"room_analysis": result["room_analysis"]},
                    constraints={"budget": budget} if budget else {},
                )
                
                design_result = await design_agent.run(design_task)
                
                if design_result.is_success:
                    result["design_recommendations"] = design_result.data.get("design", {})
                    logger.info("design_generation_complete", workflow_id=workflow_id)
                else:
                    result["errors"].append("Design generation failed")
                    
            except Exception as e:
                logger.error("design_generation_error", error=str(e))
                result["errors"].append(f"Design error: {str(e)}")
        
        # Step 3: Generate AI Render (if enabled)
        if generate_render:
            image_gen_agent = agent_registry.get("image_generation_agent")
            if image_gen_agent:
                try:
                    image_gen_task = AgentTask(
                        task_id=f"{workflow_id}_render",
                        task_type="generate_room_render",
                        agent_name="image_generation_agent",
                        parameters={"image_path": image_path},
                        context={
                            "design": result["design_recommendations"],
                            "room_analysis": result["room_analysis"],
                        },
                    )
                    
                    image_gen_result = await image_gen_agent.run(image_gen_task)
                    
                    if image_gen_result.is_success:
                        generated_path = image_gen_result.data.get("generated_image_path")
                        generated_filename = Path(generated_path).name
                        result["generated_image_url"] = f"/api/uploads/{user_id}/{generated_filename}"
                        logger.info("image_generation_complete", workflow_id=workflow_id)
                        
                        # Create before/after comparison
                        try:
                            comparison_task = AgentTask(
                                task_id=f"{workflow_id}_comparison",
                                task_type="before_after_comparison",
                                agent_name="image_generation_agent",
                                parameters={
                                    "before_image_path": image_path,
                                    "after_image_path": generated_path,
                                },
                            )
                            
                            comparison_result = await image_gen_agent.run(comparison_task)
                            
                            if comparison_result.is_success:
                                comparison_path = comparison_result.data.get("comparison_image_path")
                                comparison_filename = Path(comparison_path).name
                                result["comparison_image_url"] = f"/api/uploads/{user_id}/{comparison_filename}"
                                logger.info("comparison_created", workflow_id=workflow_id)
                        except Exception as e:
                            logger.warning("comparison_failed", error=str(e))
                    else:
                        result["errors"].append("Image generation failed")
                        logger.warning("image_generation_failed", errors=image_gen_result.errors)
                        
                except Exception as e:
                    logger.error("image_generation_error", error=str(e))
                    result["errors"].append(f"Render error: {str(e)}")
            else:
                result["errors"].append("Image generation agent not available")
        
        # Create summary
        result["summary"] = _create_summary(result)
        
        # Remove internal paths from response
        result.pop("original_image_path", None)
        
        logger.info(
            "design_studio_workflow_complete",
            workflow_id=workflow_id,
            has_render=bool(result["generated_image_url"]),
            error_count=len(result["errors"]),
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error("design_studio_error", error=str(e))
        return jsonify({
            "status": "error",
            "message": f"Workflow error: {str(e)}"
        }), 500


@design_studio_bp.route("/regenerate-render", methods=["POST"])
@jwt_required()
async def regenerate_render():
    """
    Regenerate just the AI render without re-analyzing.
    
    Request:
    {
        "original_image_path": "...",
        "design_recommendations": {...},
        "room_analysis": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        original_image_path = data.get("original_image_path")
        design_data = data.get("design_recommendations", {})
        room_analysis = data.get("room_analysis", {})
        
        # If it is a URL, parse it to get the local file path
        if original_image_path and ("/api/uploads/" in original_image_path or "/uploads/" in original_image_path):
            path_part = original_image_path.split("/uploads/")[-1]
            parts = path_part.split("/")
            if len(parts) >= 2:
                path_user_id = parts[0]
                filename = parts[1]
                original_image_path = str(Path(settings.storage.UPLOAD_DIR) / path_user_id / filename)
        
        if not original_image_path:
            return jsonify({
                "status": "error",
                "message": "original_image_path is required"
            }), 400
        
        image_gen_agent = agent_registry.get("image_generation_agent")
        if not image_gen_agent:
            return jsonify({
                "status": "error",
                "message": "Image generation agent not available"
            }), 503
        
        task = AgentTask(
            task_id=f"regen_{uuid.uuid4().hex[:8]}",
            task_type="generate_room_render",
            agent_name="image_generation_agent",
            parameters={"image_path": original_image_path},
            context={
                "design": design_data,
                "room_analysis": room_analysis,
            },
        )
        
        result = await image_gen_agent.run(task)
        
        if result.is_success:
            generated_path = result.data.get("generated_image_path")
            generated_filename = Path(generated_path).name
            
            return jsonify({
                "status": "success",
                "generated_image_url": f"/api/uploads/{user_id}/{generated_filename}",
                "prompt_used": result.data.get("prompt_used"),
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Regeneration failed",
                "errors": result.errors,
            }), 500
            
    except Exception as e:
        logger.error("regenerate_render_error", error=str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def _create_summary(result: dict) -> str:
    """Create user-friendly summary."""
    parts = []
    
    room_analysis = result.get("room_analysis", {})
    if room_analysis:
        lighting = room_analysis.get("lighting_analysis", {}).get("classification", "unknown")
        parts.append(f"Room analyzed with {lighting} lighting")
    
    design = result.get("design_recommendations", {})
    if design:
        design_title = design.get("design_title", "Custom Design")
        furniture_count = len(design.get("furniture_list", []))
        parts.append(f"{design_title} with {furniture_count} furniture items")
    
    if result.get("generated_image_url"):
        parts.append("AI render generated successfully")
    
    return " | ".join(parts) if parts else "Design complete"
