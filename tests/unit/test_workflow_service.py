"""
Unit tests for Workflow Service
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.services.workflow_service import WorkflowService


class TestWorkflowService:
    """Test Workflow Service"""
    
    def test_find_images(self, temp_dir):
        """Test finding images in folder"""
        folder_path = Path(temp_dir) / "test_folder"
        folder_path.mkdir()
        
        # Create various files
        (folder_path / "image1.png").write_bytes(b'test')
        (folder_path / "image2.jpg").write_bytes(b'test')
        (folder_path / "image3.txt").write_bytes(b'test')
        (folder_path / "image4.PNG").write_bytes(b'test')
        
        service = WorkflowService()
        images = service._find_images(str(folder_path))
        
        assert len(images) == 3  # png, jpg, PNG (case insensitive)
        assert any("image1.png" in str(img) for img in images)
        assert any("image2.jpg" in str(img) for img in images)
    
    def test_find_images_empty_folder(self, temp_dir):
        """Test finding images in empty folder"""
        folder_path = Path(temp_dir) / "empty_folder"
        folder_path.mkdir()
        
        service = WorkflowService()
        images = service._find_images(str(folder_path))
        
        assert len(images) == 0
    
    @patch('app.services.workflow_service.agent_manager.get_agent')
    @patch('app.services.workflow_service.agent_manager.get_api_client')
    @patch('app.services.workflow_service.agent_manager.get_error_handler')
    def test_process_folder_one_image(self, mock_get_error_handler, mock_get_api, mock_get_agent, temp_dir, sample_folder_name):
        """Test processing folder with 1 image"""
        # Create test folder (replace : with - for Windows compatibility)
        safe_folder_name = sample_folder_name.replace(":", "-")
        folder_path = Path(temp_dir) / safe_folder_name
        folder_path.mkdir()
        
        # Create test image
        test_image = folder_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        
        # Mock agent - batch processing
        mock_agent = Mock()
        mock_agent.process_images_batch.return_value = [
            {
                "image_id": 1,
                "success": True,
                "url": "https://example.com",
                "detected_link_id": "uuid-456",
                "error": None,
                "error_type": None
            }
        ]
        mock_get_agent.return_value = mock_agent
        
        # Mock API client
        mock_api = Mock()
        mock_api.get_sport_id.return_value = ("uuid-123", None)
        mock_get_api.return_value = mock_api
        
        # Mock error handler
        mock_error_handler = Mock()
        mock_get_error_handler.return_value = mock_error_handler
        
        service = WorkflowService()
        # Mock parse_folder_name to return parsed data for safe folder name
        with patch('app.services.workflow_service.parse_folder_name') as mock_parse:
            mock_parse.return_value = (
                "2026-01-02 00:30",
                "PL 25_26",
                "Crystal Palace - Fulham",
                "02.01.26 00-30"
            )
            result = service.process_folder(str(folder_path))
        
        assert result["success"] is True
        assert result["sport_id"] == "uuid-123"
        assert result["images_processed"] == 1
        assert result["images_success"] == 1
        assert result["images_failed"] == 0
        assert len(result["image_results"]) == 1
        assert result["image_results"][0]["index"] == 1
    
    @patch('app.services.workflow_service.agent_manager.get_agent')
    @patch('app.services.workflow_service.agent_manager.get_api_client')
    @patch('app.services.workflow_service.agent_manager.get_error_handler')
    def test_process_folder_two_images(self, mock_get_error_handler, mock_get_api, mock_get_agent, temp_dir, sample_folder_name):
        """Test processing folder with 2 images - both succeed"""
        # Create test folder (replace : with - for Windows compatibility)
        safe_folder_name = sample_folder_name.replace(":", "-")
        folder_path = Path(temp_dir) / safe_folder_name
        folder_path.mkdir()
        
        # Create 2 test images
        (folder_path / "image1.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        (folder_path / "image2.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        
        # Mock agent - batch processing with 2 images
        mock_agent = Mock()
        mock_agent.process_images_batch.return_value = [
            {
                "image_id": 1,
                "success": True,
                "url": "https://example1.com",
                "detected_link_id": "uuid-1",
                "error": None,
                "error_type": None
            },
            {
                "image_id": 2,
                "success": True,
                "url": "https://example2.com",
                "detected_link_id": "uuid-2",
                "error": None,
                "error_type": None
            }
        ]
        mock_get_agent.return_value = mock_agent
        
        # Mock API client
        mock_api = Mock()
        mock_api.get_sport_id.return_value = ("uuid-123", None)
        mock_get_api.return_value = mock_api
        
        # Mock error handler
        mock_error_handler = Mock()
        mock_get_error_handler.return_value = mock_error_handler
        
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
        assert result["sport_id"] == "uuid-123"
        assert result["images_processed"] == 2
        assert result["images_success"] == 2
        assert result["images_failed"] == 0
        assert len(result["image_results"]) == 2
        assert result["image_results"][0]["index"] == 1
        assert result["image_results"][1]["index"] == 2
        # Verify agent was called once with batch of 2
        assert mock_agent.process_images_batch.call_count == 1
        batch_payload = mock_agent.process_images_batch.call_args[0][0]
        assert len(batch_payload) == 2
    
    @patch('app.services.workflow_service.agent_manager.get_agent')
    @patch('app.services.workflow_service.agent_manager.get_api_client')
    @patch('app.services.workflow_service.agent_manager.get_error_handler')
    def test_process_folder_three_images_two_batches(self, mock_get_error_handler, mock_get_api, mock_get_agent, temp_dir, sample_folder_name):
        """Test processing folder with 3 images - should create 2 batches (2 + 1)"""
        # Create test folder (replace : with - for Windows compatibility)
        safe_folder_name = sample_folder_name.replace(":", "-")
        folder_path = Path(temp_dir) / safe_folder_name
        folder_path.mkdir()
        
        # Create 3 test images
        (folder_path / "image1.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        (folder_path / "image2.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        (folder_path / "image3.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        
        # Mock agent - will be called twice: first with 2 images, then with 1
        mock_agent = Mock()
        mock_agent.process_images_batch.side_effect = [
            [
                {
                    "image_id": 1,
                    "success": True,
                    "url": "https://example1.com",
                    "detected_link_id": "uuid-1",
                    "error": None,
                    "error_type": None
                },
                {
                    "image_id": 2,
                    "success": True,
                    "url": "https://example2.com",
                    "detected_link_id": "uuid-2",
                    "error": None,
                    "error_type": None
                }
            ],
            [
                {
                    "image_id": 3,
                    "success": True,
                    "url": "https://example3.com",
                    "detected_link_id": "uuid-3",
                    "error": None,
                    "error_type": None
                }
            ]
        ]
        mock_get_agent.return_value = mock_agent
        
        # Mock API client
        mock_api = Mock()
        mock_api.get_sport_id.return_value = ("uuid-123", None)
        mock_get_api.return_value = mock_api
        
        # Mock error handler
        mock_error_handler = Mock()
        mock_get_error_handler.return_value = mock_error_handler
        
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
        assert result["sport_id"] == "uuid-123"
        assert result["images_processed"] == 3
        assert result["images_success"] == 3
        assert result["images_failed"] == 0
        assert len(result["image_results"]) == 3
        # Verify agent was called twice: once with 2 images, once with 1
        assert mock_agent.process_images_batch.call_count == 2
        first_batch = mock_agent.process_images_batch.call_args_list[0][0][0]
        second_batch = mock_agent.process_images_batch.call_args_list[1][0][0]
        assert len(first_batch) == 2
        assert len(second_batch) == 1
    
    @patch('app.services.workflow_service.agent_manager.get_agent')
    @patch('app.services.workflow_service.agent_manager.get_api_client')
    @patch('app.services.workflow_service.agent_manager.get_error_handler')
    def test_process_folder_one_fail_one_success(self, mock_get_error_handler, mock_get_api, mock_get_agent, temp_dir, sample_folder_name):
        """Test processing folder with 2 images - 1 fails, 1 succeeds"""
        # Create test folder (replace : with - for Windows compatibility)
        safe_folder_name = sample_folder_name.replace(":", "-")
        folder_path = Path(temp_dir) / safe_folder_name
        folder_path.mkdir()
        
        # Create 2 test images
        (folder_path / "image1.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        (folder_path / "image2.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        
        # Mock agent - batch processing: 1 fails, 1 succeeds
        mock_agent = Mock()
        mock_agent.process_images_batch.return_value = [
            {
                "image_id": 1,
                "success": False,
                "url": None,
                "detected_link_id": None,
                "error": "Extraction failed",
                "error_type": "extract_error"
            },
            {
                "image_id": 2,
                "success": True,
                "url": "https://example2.com",
                "detected_link_id": "uuid-2",
                "error": None,
                "error_type": None
            }
        ]
        mock_get_agent.return_value = mock_agent
        
        # Mock API client
        mock_api = Mock()
        mock_api.get_sport_id.return_value = ("uuid-123", None)
        mock_get_api.return_value = mock_api
        
        # Mock error handler
        mock_error_handler = Mock()
        mock_get_error_handler.return_value = mock_error_handler
        
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
        assert result["sport_id"] == "uuid-123"
        assert result["images_processed"] == 2
        assert result["images_success"] == 1
        assert result["images_failed"] == 1
        assert len(result["image_results"]) == 2
        assert result["image_results"][0]["index"] == 1
        assert result["image_results"][0]["success"] is False
        assert result["image_results"][1]["index"] == 2
        assert result["image_results"][1]["success"] is True
    
    def test_process_folder_parse_error(self, temp_dir):
        """Test processing folder with parse error"""
        folder_path = Path(temp_dir) / "Invalid Folder Name"
        folder_path.mkdir()
        
        service = WorkflowService()
        result = service.process_folder(str(folder_path))
        
        assert result["success"] is False
        assert "Cannot parse" in result["error"]
    
    @patch('app.services.workflow_service.agent_manager.get_api_client')
    def test_process_folder_api_error(self, mock_get_api, temp_dir, sample_folder_name):
        """Test processing folder with API error"""
        # Create test folder (replace : with - for Windows compatibility)
        safe_folder_name = sample_folder_name.replace(":", "-")
        folder_path = Path(temp_dir) / safe_folder_name
        folder_path.mkdir()
        
        mock_api = Mock()
        mock_api.get_sport_id.return_value = (None, "API Error")
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
        
        assert result["success"] is False
        assert "Cannot get sport_id" in result["error"]
    
    def test_save_results(self, temp_dir):
        """Test saving results"""
        import json
        
        service = WorkflowService()
        results = [
            {
                "folder": "test",
                "success": True,
                "images_processed": 1
            }
        ]
        
        output_file = str(Path(temp_dir) / "results.json")
        service.save_results(results, output_file)
        
        assert Path(output_file).exists()
        
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["total_folders"] == 1
        assert data["total_images_processed"] == 1
