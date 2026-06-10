# Setup Local AI Services for Image Generation

This guide helps you set up local AI model services for image generation and vision analysis.

## Prerequisites

- **GPU**: NVIDIA GPU with 8GB+ VRAM (recommended for SDXL)
- **RAM**: 16GB+ system RAM
- **Storage**: 50GB+ free space for models
- **Python**: 3.10 or 3.11
- **CUDA**: 11.8 or 12.x (for NVIDIA GPUs)

## Quick Start (Docker - Easiest)

### Option 1: Using Docker Compose

Create `docker-compose.ai-services.yml`:

```yaml
version: '3.8'

services:
  # Stable Diffusion XL - Image Generation
  sdxl-service:
    image: stability-ai/sdxl:latest
    ports:
      - "8004:8004"
    environment:
      - MODEL_NAME=stabilityai/stable-diffusion-xl-base-1.0
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  # Florence2 - Vision Analysis
  florence2-service:
    image: huggingface/transformers:latest
    ports:
      - "8001:8001"
    environment:
      - MODEL_NAME=microsoft/Florence-2-large
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  # YOLOv11 - Object Detection
  yolo-service:
    image: ultralytics/yolov8:latest
    ports:
      - "8002:8002"
    environment:
      - MODEL_NAME=yolo11n.pt
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  # SAM2 - Segmentation
  sam2-service:
    image: facebook/segment-anything-2:latest
    ports:
      - "8003:8003"
    environment:
      - MODEL_NAME=sam2_hiera_large
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

Start services:
```bash
docker-compose -f docker-compose.ai-services.yml up -d
```

## Manual Setup (Python)

### 1. Setup Stable Diffusion XL (Port 8004)

```bash
# Create virtual environment
python -m venv venv-sdxl
.\venv-sdxl\Scripts\activate

# Install dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install diffusers transformers accelerate safetensors
pip install fastapi uvicorn pillow

# Create service file: sdxl_service.py
```

```python
# sdxl_service.py
from fastapi import FastAPI, File, UploadFile, Form
from diffusers import StableDiffusionXLPipeline
import torch
from PIL import Image
import io
import base64

app = FastAPI()

# Load model
pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    use_safetensors=True,
    variant="fp16"
).to("cuda")

@app.post("/v1/image/generate")
async def generate_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    strength: float = Form(0.8)
):
    # Load input image
    input_image = Image.open(io.BytesIO(await image.read()))
    
    # Generate
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=input_image,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        strength=strength
    ).images[0]
    
    # Convert to base64
    buffer = io.BytesIO()
    result.save(buffer, format="JPEG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {"image": img_b64}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

Run:
```bash
uvicorn sdxl_service:app --host 0.0.0.0 --port 8004
```

### 2. Setup Florence2 Vision (Port 8001)

```bash
# Create virtual environment
python -m venv venv-florence
.\venv-florence\Scripts\activate

# Install dependencies
pip install torch torchvision
pip install transformers pillow
pip install fastapi uvicorn

# Create service file: florence2_service.py
```

```python
# florence2_service.py
from fastapi import FastAPI, File, UploadFile
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import torch
import io

app = FastAPI()

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-large",
    torch_dtype=torch.float16,
    trust_remote_code=True
).to("cuda")

processor = AutoProcessor.from_pretrained(
    "microsoft/Florence-2-large",
    trust_remote_code=True
)

@app.post("/v1/vision/florence2")
async def analyze_image(image: UploadFile = File(...)):
    img = Image.open(io.BytesIO(await image.read()))
    
    # Run analysis
    inputs = processor(images=img, return_tensors="pt").to("cuda")
    generated_ids = model.generate(**inputs, max_new_tokens=1024)
    result = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    return {"analysis": result}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

Run:
```bash
uvicorn florence2_service:app --host 0.0.0.0 --port 8001
```

### 3. Setup YOLO (Port 8002)

```bash
pip install ultralytics fastapi uvicorn
```

```python
# yolo_service.py
from fastapi import FastAPI, File, UploadFile
from ultralytics import YOLO
from PIL import Image
import io

app = FastAPI()
model = YOLO("yolo11n.pt")

@app.post("/v1/vision/yolo")
async def detect_objects(image: UploadFile = File(...)):
    img = Image.open(io.BytesIO(await image.read()))
    results = model(img)
    
    detections = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "class": r.names[int(box.cls)],
                "confidence": float(box.conf),
                "bbox": box.xyxy[0].tolist()
            })
    
    return {"detections": detections}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### 4. Setup SAM2 (Port 8003)

```bash
pip install git+https://github.com/facebookresearch/segment-anything-2.git
pip install fastapi uvicorn
```

```python
# sam2_service.py
from fastapi import FastAPI, File, UploadFile
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from PIL import Image
import torch
import io
import numpy as np

app = FastAPI()

checkpoint = "./checkpoints/sam2_hiera_large.pt"
model_cfg = "sam2_hiera_l.yaml"
predictor = SAM2ImagePredictor(build_sam2(model_cfg, checkpoint))

@app.post("/v1/vision/sam2")
async def segment_image(image: UploadFile = File(...)):
    img = Image.open(io.BytesIO(await image.read()))
    img_array = np.array(img)
    
    predictor.set_image(img_array)
    
    # Auto-segment everything
    masks, scores, _ = predictor.predict(
        point_coords=None,
        point_labels=None,
        multimask_output=True
    )
    
    return {
        "num_segments": len(masks),
        "scores": scores.tolist()
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## Lightweight Alternative (CPU Only)

If you don't have a GPU, use these lightweight alternatives:

### Mini SDXL (CPU)
```python
from diffusers import StableDiffusionPipeline
pipe = StableDiffusionPipeline.from_pretrained(
    "segmind/small-sd",  # Smaller, faster model
    torch_dtype=torch.float32
)
```

### BLIP for Vision (CPU)
```python
from transformers import BlipProcessor, BlipForConditionalGeneration
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
```

## Testing Services

Run the check script:
```bash
python check_services.py
```

Or test manually:
```bash
# Test SDXL
curl http://localhost:8004/health

# Test Florence2
curl http://localhost:8001/health

# Test YOLO
curl http://localhost:8002/health

# Test SAM2
curl http://localhost:8003/health
```

## Troubleshooting

### Out of Memory
- Reduce image size
- Use lower precision (float16)
- Use smaller models
- Close other applications

### CUDA Not Available
```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Install correct CUDA toolkit
# For CUDA 11.8:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Slow Generation
- Use GPU if available
- Reduce `num_inference_steps` (20-30)
- Use smaller models
- Enable `xformers` for faster attention:
```bash
pip install xformers
pipe.enable_xformers_memory_efficient_attention()
```

## Cloud Alternatives (No Local GPU Needed)

If local setup is too complex:

1. **Hugging Face Inference API** (free tier)
2. **Replicate** (pay per use, ~$0.01 per image)
3. **RunPod** (GPU rental, ~$0.20/hour)
4. **Modal** (serverless GPU, generous free tier)

See `IMAGE_GENERATION_FIX.md` for configuration details.
