"""
Integration tests for workflow service
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from app.services.workflow_service import WorkflowService


class TestWorkflowService:
    """Test workflow service integration"""
    
    def test_process_folder_success(self, temp_dir, sample_folder_name):
        """Test processing a folder successfully"""
        # Create test folder structure (replace : with - for Windows compatibility)
        safe_folder_name = sample_folder_name.replace(":", "-")
        folder_path = Path(temp_dir) / safe_folder_name
        folder_path.mkdir()
        
        # Create test image
        test_image = folder_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        
        with patch('app.core.agent_manager.agent_manager.get_agent') as mock_get_agent, \
             patch('app.core.agent_manager.agent_manager.get_api_client') as mock_get_api:
            
            # Mock agent
            mock_agent = Mock()
            mock_agent.process_image.return_value = {
                "success": True,
                "url": "https://example.com",
                "detected_link_id": 456,
                "error": None,
                "error_type": None
            }
            mock_get_agent.return_value = mock_agent
            
            # Mock API client
            mock_api = Mock()
            mock_api.get_sport_id.return_value = (123, None)
            mock_get_api.return_value = mock_api
            
            service = WorkflowService()
            # Mock parse_folder_name to return parsed data
            with patch('app.services.workflow_service.parse_folder_name') as mock_parse:
                mock_parse.return_value = (
                    "2026-01-02 00:30",
                    "PL 25_26",
                    "Crystal Palace - Fulham",
                    "02.01.26 00-30"
                )
                result = service.process_folder(str(folder_path))
            
            assert result["success"] is True
            assert result["sport_id"] == 123
            assert result["images_processed"] == 1
            assert result["images_success"] == 1
    
    def test_process_folder_parse_error(self, temp_dir):
        """Test processing folder with parse error"""
        folder_path = Path(temp_dir) / "Invalid Folder Name"
        folder_path.mkdir()
        
        service = WorkflowService()
        result = service.process_folder(str(folder_path))
        
        assert result["success"] is False
        assert "Cannot parse" in result["error"]
    
    def test_find_images(self, temp_dir):
        """Test finding images in folder"""
        folder_path = Path(temp_dir) / "test_folder"
        folder_path.mkdir()
        
        # Create various image files
        (folder_path / "image1.png").write_bytes(b'test')
        (folder_path / "image2.jpg").write_bytes(b'test')
        (folder_path / "image3.txt").write_bytes(b'test')
        
        service = WorkflowService()
        images = service._find_images(str(folder_path))
        
        assert len(images) == 2
        assert any("image1.png" in str(img) for img in images)
        assert any("image2.jpg" in str(img) for img in images)
