"""
Gruha Alankara — Image Generation API Routes

Endpoints for generating rendered room images with furniture.
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path

from app.agents.image_generation_agent import ImageGenerationAgent
from app.agents.schemas import AgentTask
from app.database.mongo import log_agent_execution
from config.logging_config import get_logger

logger = get_logger(__name__)

image_gen_bp = Blueprint("image_gen", __name__, url_prefix="/api/image-generation")


@image_gen_bp.route("/generate-room-render", methods=["POST"])
async def generate_room_render():
    """
    Generate a photorealistic room render with furniture.
    
    Request:
    {
        "image_path": "/path/to/uploaded/room.jpg",
        "design_data": {...},  # From design agent
        "room_analysis": {...}  # From vision agent
    }
    
    Response:
    {
        "status": "success",
        "generated_image_path": "/path/to/generated.jpg",
        "generated_image_url": "/api/image-generation/view/generated.jpg",
        "original_image_path": "/path/to/original.jpg",
        "prompt_used": "...",
        "task_id": "..."
    }
    """
    try:
        data = request.get_json()
        
        image_path = data.get("image_path")
        design_data = data.get("design_data", {})
        room_analysis = data.get("room_analysis", {})
        user_id = data.get("user_id", "")
        
        if not image_path:
            return jsonify({
                "status": "error",
                "message": "image_path is required"
            }), 400
        
        # Create agent task
        agent = ImageGenerationAgent()
        task = AgentTask(
            task_id=f"img_gen_{user_id[:8]}",
            task_type="generate_room_render",
            agent_name=agent.name,
            parameters={"image_path": image_path},
            context={
                "design": design_data,
                "room_analysis": room_analysis,
            },
        )
        
        # Execute
        result = await agent.run(task)
        
        # Log execution
        try:
            log_agent_execution(
                agent_name=agent.name,
                task_type="generate_room_render",
                user_id=user_id,
                status=result.status.value,
                duration_ms=result.duration_ms,
            )
        except Exception:
            pass
        
        if result.is_success:
            generated_path = result.data.get("generated_image_path")
            filename = Path(generated_path).name
            
            return jsonify({
                "status": "success",
                "generated_image_path": generated_path,
                "generated_image_url": f"/api/image-generation/view/{filename}",
                "original_image_path": result.data.get("original_image_path"),
                "prompt_used": result.data.get("prompt_used"),
                "design_applied": result.data.get("design_applied"),
                "task_id": task.task_id,
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Image generation failed",
                "errors": result.errors,
            }), 500
            
    except Exception as e:
        logger.error("generate_room_render_error", error=str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@image_gen_bp.route("/add-furniture", methods=["POST"])
async def add_furniture():
    """
    Add specific furniture items to a room image.
    
    Request:
    {
        "image_path": "/path/to/room.jpg",
        "furniture_list": [
            {"item": "sofa", "description": "modern grey sectional sofa"},
            {"item": "coffee table", "description": "wooden round coffee table"}
        ],
        "placement_areas": [
            {"x": 100, "y": 200, "width": 300, "height": 200},
            {"x": 250, "y": 400, "width": 150, "height": 100}
        ]
    }
    """
    try:
        data = request.get_json()
        
        image_path = data.get("image_path")
        furniture_list = data.get("furniture_list", [])
        placement_areas = data.get("placement_areas", [])
        user_id = data.get("user_id", "")
        
        if not image_path:
            return jsonify({"status": "error", "message": "image_path is required"}), 400
        
        agent = ImageGenerationAgent()
        task = AgentTask(
            task_id=f"add_furn_{user_id[:8]}",
            task_type="add_furniture_to_room",
            agent_name=agent.name,
            parameters={
                "image_path": image_path,
                "furniture_list": furniture_list,
                "placement_areas": placement_areas,
            },
        )
        
        result = await agent.run(task)
        
        if result.is_success:
            generated_path = result.data.get("generated_image_path")
            filename = Path(generated_path).name
            
            return jsonify({
                "status": "success",
                "generated_image_path": generated_path,
                "generated_image_url": f"/api/image-generation/view/{filename}",
                "furniture_added": result.data.get("furniture_added"),
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to add furniture",
                "errors": result.errors,
            }), 500
            
    except Exception as e:
        logger.error("add_furniture_error", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@image_gen_bp.route("/before-after", methods=["POST"])
async def create_before_after():
    """
    Create a before/after comparison image.
    
    Request:
    {
        "before_image_path": "/path/to/before.jpg",
        "after_image_path": "/path/to/after.jpg"
    }
    """
    try:
        data = request.get_json()
        
        before_path = data.get("before_image_path")
        after_path = data.get("after_image_path")
        
        if not before_path or not after_path:
            return jsonify({
                "status": "error",
                "message": "Both before_image_path and after_image_path are required"
            }), 400
        
        agent = ImageGenerationAgent()
        task = AgentTask(
            task_id="comparison",
            task_type="before_after_comparison",
            agent_name=agent.name,
            parameters={
                "before_image_path": before_path,
                "after_image_path": after_path,
            },
        )
        
        result = await agent.run(task)
        
        if result.is_success:
            comparison_path = result.data.get("comparison_image_path")
            filename = Path(comparison_path).name
            
            return jsonify({
                "status": "success",
                "comparison_image_path": comparison_path,
                "comparison_image_url": f"/api/image-generation/view/{filename}",
                "before_path": before_path,
                "after_path": after_path,
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to create comparison",
                "errors": result.errors,
            }), 500
            
    except Exception as e:
        logger.error("before_after_error", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@image_gen_bp.route("/view/<filename>", methods=["GET"])
def view_generated_image(filename: str):
    """
    View a generated image.
    """
    try:
        from config.settings import settings
        file_path = Path(settings.storage.UPLOAD_DIR) / filename
        
        if not file_path.exists():
            return jsonify({"status": "error", "message": "Image not found"}), 404
        
        return send_file(file_path, mimetype="image/jpeg")
        
    except Exception as e:
        logger.error("view_image_error", error=str(e))
        return jsonify({"status": "error", "message": str(e)}), 500
