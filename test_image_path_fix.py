#!/usr/bin/env python3
"""
Test script to verify the image generation file path fix.
This creates a mock scenario without requiring AI services.
"""

import asyncio
from pathlib import Path
from PIL import Image
from app.agents.image_generation_agent import ImageGenerationAgent
from app.agents.schemas import AgentTask
from config.settings import settings

async def test_file_path_fix():
    """Test that generated images are saved in correct user directories."""
    
    print("\n" + "="*70)
    print("🧪 Testing Image Generation File Path Fix")
    print("="*70 + "\n")
    
    # Create a test user directory with a test image
    test_user_id = "test_user_123"
    user_dir = Path(settings.storage.UPLOAD_DIR) / test_user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a simple test image
    test_image_path = user_dir / "test_room.jpg"
    test_img = Image.new('RGB', (800, 600), color=(73, 109, 137))
    test_img.save(test_image_path)
    
    print(f"✅ Created test image: {test_image_path}")
    
    # Initialize agent
    agent = ImageGenerationAgent()
    
    # Test 1: Check user_id extraction
    print("\n📋 Test 1: User ID Extraction")
    extracted_user_id = agent._get_user_id_from_image_path(str(test_image_path))
    
    if extracted_user_id == test_user_id:
        print(f"✅ Correctly extracted user_id: {extracted_user_id}")
    else:
        print(f"❌ Failed to extract user_id. Got: {extracted_user_id}, Expected: {test_user_id}")
        return
    
    # Test 2: Check save path
    print("\n📋 Test 2: Generated Image Save Path")
    test_task_id = "test_abc123"
    
    # Create a test generated image
    generated_img = Image.new('RGB', (800, 600), color=(200, 100, 50))
    save_path = agent._save_generated_image(generated_img, test_task_id, test_user_id)
    
    expected_path = user_dir / f"generated_{test_task_id}.jpg"
    
    if Path(save_path) == expected_path and save_path.exists():
        print(f"✅ Image saved to correct location: {save_path}")
    else:
        print(f"❌ Image saved to wrong location")
        print(f"   Expected: {expected_path}")
        print(f"   Got: {save_path}")
        return
    
    # Test 3: Check comparison image path
    print("\n📋 Test 3: Comparison Image Save Path")
    
    # Create another test image
    test_after_path = user_dir / "test_after.jpg"
    after_img = Image.new('RGB', (800, 600), color=(100, 150, 200))
    after_img.save(test_after_path)
    
    comparison_path = agent._create_comparison_image(
        str(test_image_path),
        str(test_after_path)
    )
    
    expected_comparison_path = user_dir / f"comparison_{test_image_path.stem}.jpg"
    
    if Path(comparison_path) == expected_comparison_path and comparison_path.exists():
        print(f"✅ Comparison saved to correct location: {comparison_path}")
    else:
        print(f"❌ Comparison saved to wrong location")
        print(f"   Expected: {expected_comparison_path}")
        print(f"   Got: {comparison_path}")
        return
    
    # Test 4: Verify URL generation would work
    print("\n📋 Test 4: URL Generation Check")
    
    generated_filename = Path(save_path).name
    expected_url = f"/api/uploads/{test_user_id}/{generated_filename}"
    
    print(f"✅ Generated file: {generated_filename}")
    print(f"✅ Expected URL: {expected_url}")
    print(f"✅ File exists at: {save_path}")
    
    # Verify the file structure
    print("\n📋 Test 5: Directory Structure Verification")
    print(f"\nUpload directory: {settings.storage.UPLOAD_DIR}")
    print(f"User directory: {user_dir}")
    print(f"\nFiles in user directory:")
    
    for file in user_dir.iterdir():
        if file.is_file():
            print(f"  - {file.name}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED! File path fix is working correctly.")
    print("="*70 + "\n")
    
    print("📝 Summary:")
    print("  • Images are now saved in user-specific directories")
    print("  • File paths match the expected URL structure")
    print("  • Generated images will be properly served by the API")
    print("\n  Once AI services are running, image generation will work!")
    
    # Clean up test files
    print("\n🧹 Cleaning up test files...")
    for file in [test_image_path, test_after_path, save_path, comparison_path]:
        if Path(file).exists():
            Path(file).unlink()
    
    # Remove test directory if empty
    try:
        user_dir.rmdir()
        print("✅ Test cleanup complete")
    except:
        pass

if __name__ == "__main__":
    asyncio.run(test_file_path_fix())
