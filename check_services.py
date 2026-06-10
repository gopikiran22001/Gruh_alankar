#!/usr/bin/env python3
"""
Check which AI services are running and which need to be started.
"""

import httpx
import asyncio
from config.settings import settings

SERVICES = {
    "SDXL Image Generation": settings.image_gen.SDXL_ENDPOINT,
    "ControlNet": settings.image_gen.CONTROLNET_ENDPOINT,
    "Florence2 Vision": "http://localhost:8001",
    "YOLOv11 Detection": "http://localhost:8002",
    "SAM2 Segmentation": "http://localhost:8003",
}

async def check_service(name: str, url: str) -> tuple[str, bool, str]:
    """Check if a service is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try health endpoint first, then root
            for endpoint in [f"{url}/health", url]:
                try:
                    response = await client.get(endpoint)
                    if response.status_code < 500:
                        return (name, True, f"✅ Running at {url}")
                except:
                    continue
            return (name, False, f"❌ Not responding at {url}")
    except Exception as e:
        return (name, False, f"❌ Not responding at {url}")

async def main():
    print("\n" + "="*60)
    print("🔍 Gruha Alankara - Service Health Check")
    print("="*60 + "\n")
    
    tasks = [check_service(name, url) for name, url in SERVICES.items()]
    results = await asyncio.gather(*tasks)
    
    running_count = sum(1 for _, is_running, _ in results if is_running)
    total_count = len(results)
    
    for name, is_running, message in results:
        print(f"{message}")
    
    print("\n" + "="*60)
    print(f"Services Running: {running_count}/{total_count}")
    print("="*60 + "\n")
    
    if running_count == 0:
        print("⚠️  No AI services are running!")
        print("\nTo enable image generation, you need to:")
        print("1. Start local AI model services (requires GPU)")
        print("2. OR configure alternative API endpoints in .env")
        print("\nSee IMAGE_GENERATION_FIX.md for detailed solutions.")
    elif running_count < total_count:
        print("⚠️  Some services are not running.")
        print("Image generation will work but with reduced quality.")
    else:
        print("✅ All services are running! Image generation ready.")

if __name__ == "__main__":
    asyncio.run(main())
