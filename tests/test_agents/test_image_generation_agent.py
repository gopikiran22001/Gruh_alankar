"""Gruha Alankara — Image Generation Agent Tests."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.agents.image_generation_agent import ImageGenerationAgent
from app.agents.schemas import AgentTask, TaskStatusEnum
from PIL import Image

class TestImageGenerationAgent:
    def setup_method(self):
        self.agent = ImageGenerationAgent()

    @pytest.mark.asyncio
    @patch("app.agents.image_generation_agent.Path")
    @patch("app.agents.image_generation_agent.Image")
    async def test_image_generation_fallback_to_pollinations(self, mock_image_cls, mock_path_cls):
        # Setup mocks
        mock_path_cls.return_value.exists.return_value = True
        
        # Mock primary post request failing
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = Exception("Connection refused")
        
        # Mock fallback get request succeeding
        mock_response_success = MagicMock()
        mock_response_success.headers = {"content-type": "image/jpeg"}
        mock_response_success.content = b"fake_image_bytes"
        
        self.agent._http_client.post = AsyncMock(return_value=mock_response_fail)
        self.agent._http_client.get = AsyncMock(return_value=mock_response_success)
        
        # Mock saving generated image
        with patch.object(self.agent, "_save_generated_image") as mock_save:
            mock_save.return_value = "/fake/output/path.jpg"
            
            task = AgentTask(
                task_id="test_render",
                task_type="generate_room_render",
                agent_name="image_generation_agent",
                parameters={"image_path": "/fake/original.jpg"},
                context={
                    "design": {"style": "modern", "style_description": "modern design", "furniture_list": [{"item": "sofa"}]},
                    "room_analysis": {"lighting_analysis": {"classification": "well_lit"}}
                }
            )
            
            result = await self.agent.execute(task)
            
            assert result.status == TaskStatusEnum.SUCCESS
            assert result.data["generated_image_path"] == "/fake/output/path.jpg"
            
            # Verify fallback url was called
            self.agent._http_client.get.assert_called_once()
            args, kwargs = self.agent._http_client.get.call_args
            assert "pollinations" in args[0]

    @pytest.mark.asyncio
    @patch("app.agents.image_generation_agent.Path")
    @patch("app.agents.image_generation_agent.Image")
    async def test_image_generation_fallback_to_original_image(self, mock_image_cls, mock_path_cls):
        # Setup mocks
        mock_path_cls.return_value.exists.return_value = True
        
        # Mock primary post request failing
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = Exception("Connection refused")
        
        # Mock fallback get request also failing
        mock_fallback_fail = MagicMock()
        mock_fallback_fail.raise_for_status.side_effect = Exception("Network timeout")
        
        self.agent._http_client.post = AsyncMock(return_value=mock_response_fail)
        self.agent._http_client.get = AsyncMock(return_value=mock_fallback_fail)
        
        # Mock saving generated image
        with patch.object(self.agent, "_save_generated_image") as mock_save:
            mock_save.return_value = "/fake/output/path.jpg"
            
            task = AgentTask(
                task_id="test_render_all_fail",
                task_type="generate_room_render",
                agent_name="image_generation_agent",
                parameters={"image_path": "/fake/original.jpg"},
                context={
                    "design": {"style": "modern", "style_description": "modern design", "furniture_list": [{"item": "sofa"}]},
                    "room_analysis": {"lighting_analysis": {"classification": "well_lit"}}
                }
            )
            
            result = await self.agent.execute(task)
            
            assert result.status == TaskStatusEnum.SUCCESS
            assert result.data["generated_image_path"] == "/fake/output/path.jpg"
            
            # Verify original image was loaded as fallback
            mock_image_cls.open.assert_called_with("/fake/original.jpg")

    @pytest.mark.asyncio
    @patch("app.agents.image_generation_agent.Path")
    async def test_inpaint_furniture_fallback_to_original_image(self, mock_path_cls):
        # Setup mock for file open
        mock_path_cls.return_value.exists.return_value = True
        
        # Mock inpaint endpoint failing
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = Exception("Connection refused")
        self.agent._http_client.post = AsyncMock(return_value=mock_response_fail)
        
        # Mock _create_placement_mask
        with patch.object(self.agent, "_create_placement_mask") as mock_mask, \
             patch("builtins.open", MagicMock()):
            mock_mask.return_value = b"fake_mask_bytes"
            
            task = AgentTask(
                task_id="test_inpaint_fail",
                task_type="add_furniture_to_room",
                agent_name="image_generation_agent",
                parameters={
                    "image_path": "/fake/original.jpg",
                    "furniture_list": [{"item": "sofa", "description": "a gray sofa"}],
                    "placement_areas": [{"x": 10, "y": 10, "width": 50, "height": 50}]
                }
            )
            
            result = await self.agent.execute(task)
            
            assert result.status == TaskStatusEnum.SUCCESS
            # Since inpainting failed, the result path should fall back to the original input image path
            assert result.data["generated_image_path"] == "/fake/original.jpg"
            assert result.data["furniture_added"] == 1
