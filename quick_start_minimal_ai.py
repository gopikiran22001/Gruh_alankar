#!/usr/bin/env python3
"""
Quick Start Minimal AI Service

This is a lightweight mock service that provides basic responses
for testing the image generation workflow WITHOUT requiring GPU or heavy models.

Perfect for:
- Testing file path fixes
- Development without GPU
- CI/CD pipelines
- Quick prototyping

NOT for production - this returns mock/simple responses.
"""

from fastapi import FastAPI, File, UploadFile, Form
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import uvicorn
from datetime import datetime

app = FastAPI(title="Minimal AI Mock Service", version="1.0.0")

def create_mock_generated_image(original_image: Image.Image, prompt: str) -> Image.Image:
    """Create a simple mock 'generated' image based on the original."""
    # Create a copy
    img = original_image.copy()
    
    # Add overlay to show it's been "processed"
    draw = ImageDraw.Draw(img)
    
    # Add semi-transparent overlay
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 100))
    img_rgba = img.convert('RGBA')
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert('RGB')
    
    # Add text
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 30)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Add "AI Generated" label
    text = "AI Generated (Mock)"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (img.width - text_width) // 2
    y = img.height // 2 - text_height
    
    # Background for text
    draw.rectangle(
        [x-20, y-10, x+text_width+20, y+text_height+10],
        fill=(255, 255, 255, 200)
    )
    draw.text((x, y), text, fill=(50, 50, 50), font=font)
    
    # Add timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    draw.text((10, 10), f"Generated: {timestamp}", fill=(255, 255, 255), font=small_font)
    
    # Add prompt snippet (first 50 chars)
    prompt_text = f"Style: {prompt[:50]}..."
    draw.text((10, img.height - 30), prompt_text, fill=(255, 255, 255), font=small_font)
    
    return img

@app.get("/")
async def root():
    return {
        "service": "Minimal AI Mock Service",
        "version": "1.0.0",
        "status": "running",
        "note": "This is a mock service for testing. Use real AI services in production."
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "type": "mock"}

@app.post("/v1/image/generate")
async def generate_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    strength: float = Form(0.8)
):
    """Mock SDXL image generation endpoint."""
    
    # Load input image
    input_image = Image.open(io.BytesIO(await image.read()))
    
    # Create mock generated image
    result = create_mock_generated_image(input_image, prompt)
    
    # Convert to base64
    buffer = io.BytesIO()
    result.save(buffer, format="JPEG", quality=95)
    img_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        "image": img_b64,
        "mock": True,
        "prompt": prompt,
        "note": "This is a mock response. Install real SDXL for actual generation."
    }

@app.post("/v1/image/controlnet")
async def controlnet_generation(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    control_type: str = Form("canny")
):
    """Mock ControlNet endpoint."""
    input_image = Image.open(io.BytesIO(await image.read()))
    result = create_mock_generated_image(input_image, f"ControlNet: {prompt}")
    
    buffer = io.BytesIO()
    result.save(buffer, format="JPEG", quality=95)
    img_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {"image": img_b64, "mock": True}

@app.post("/v1/vision/florence2")
async def florence2_analysis(image: UploadFile = File(...)):
    """Mock Florence2 vision analysis."""
    return {
        "analysis": "Mock analysis: This appears to be an interior room space with furniture and decor.",
        "mock": True,
        "objects": ["furniture", "walls", "floor", "lighting"],
        "colors": ["neutral", "warm tones"],
        "note": "Install Florence2 for detailed analysis."
    }

@app.post("/v1/vision/yolo")
async def yolo_detection(image: UploadFile = File(...)):
    """Mock YOLO object detection."""
    return {
        "detections": [
            {"class": "sofa", "confidence": 0.85, "bbox": [100, 200, 400, 500]},
            {"class": "table", "confidence": 0.78, "bbox": [300, 350, 450, 480]},
            {"class": "chair", "confidence": 0.72, "bbox": [500, 300, 600, 550]},
        ],
        "mock": True,
        "note": "Install YOLOv11 for accurate detection."
    }

@app.post("/v1/vision/sam2")
async def sam2_segmentation(image: UploadFile = File(...)):
    """Mock SAM2 segmentation."""
    return {
        "num_segments": 15,
        "scores": [0.95, 0.89, 0.87, 0.85, 0.82],
        "mock": True,
        "note": "Install SAM2 for precise segmentation."
    }

def main():
    """Start all mock services on different ports."""
    import sys
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8004  # Default SDXL port
    
    print("\n" + "="*70)
    print("🚀 Starting Minimal AI Mock Service")
    print("="*70)
    print(f"\n📍 Service running on: http://localhost:{port}")
    print(f"📍 Health check: http://localhost:{port}/health")
    print(f"📍 API docs: http://localhost:{port}/docs")
    print("\n⚠️  This is a MOCK service for testing only!")
    print("   For production, use real AI models.")
    print("\n💡 To start all services:")
    print("   python quick_start_minimal_ai.py 8004  # SDXL")
    print("   python quick_start_minimal_ai.py 8001  # Florence2")
    print("   python quick_start_minimal_ai.py 8002  # YOLO")
    print("   python quick_start_minimal_ai.py 8003  # SAM2")
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
