"""
Unit tests for Image Processing Agent
"""

import pytest
from unittest.mock import Mock, patch
from app.agents.image_processing_agent import ImageProcessingAgent
from app.tools.url_extractor_tool import URLExtractorTool
from app.tools.api_tools import DetectLinkTool, UploadImageTool
from app.utils.error_handler import ErrorHandler


class TestImageProcessingAgent:
    """Test Image Processing Agent"""
    
    @pytest.fixture
    def mock_tools(self, mock_azure_client, mock_sport_api_client, temp_dir):
        """Create mock tools"""
        from pathlib import Path
        url_tool = Mock(spec=URLExtractorTool)
        url_tool.name = "extract_url"
        detect_tool = Mock(spec=DetectLinkTool)
        detect_tool.name = "detect_link"
        upload_tool = Mock(spec=UploadImageTool)
        upload_tool.name = "upload_image"
        error_handler = ErrorHandler(
            retry_file=str(Path(temp_dir) / "retry.json"),
            file_format="json"
        )
        
        return url_tool, detect_tool, upload_tool, error_handler
    
    def test_process_image_success(self, mock_tools, temp_image_file):
        """Test successful image processing"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        # Setup mocks
        url_tool.execute.return_value = ("https://example.com", None)
        detect_tool.execute.return_value = (456, None)
        upload_tool.execute.return_value = (True, None)
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        result = agent.process_image(
            image_path=temp_image_file,
            match_name="Test Match",
            sport_id=123
        )
        
        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert result["detected_link_id"] == 456
        assert result["error"] is None
    
    def test_process_image_extract_error(self, mock_tools, temp_image_file):
        """Test image processing with URL extraction error"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.return_value = (None, "Extraction failed")
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        result = agent.process_image(
            image_path=temp_image_file,
            match_name="Test Match",
            sport_id=123
        )
        
        assert result["success"] is False
        assert result["error_type"] == "extract_error"
        assert "Extraction failed" in result["error"]
    
    def test_process_image_detect_error(self, mock_tools, temp_image_file):
        """Test image processing with link detection error"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.return_value = ("https://example.com", None)
        detect_tool.execute.return_value = (None, "Detection failed")
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        result = agent.process_image(
            image_path=temp_image_file,
            match_name="Test Match",
            sport_id=123
        )
        
        assert result["success"] is False
        assert result["error_type"] == "detect_error"
        assert result["url"] == "https://example.com"  # URL was extracted
    
    def test_process_image_rescue_similarity(self, mock_tools, temp_image_file):
        """Rescue flow: similarity >= 0.85 chọn luôn detected_link_id."""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        ocr_url = "https://example.com/path"
        url_tool.execute.return_value = (ocr_url, None)
        # check_exists không tìm thấy nhưng không báo lỗi
        detect_tool.execute.return_value = (None, None)
        
        # Mock api_client trên detect_tool
        api_client = Mock()
        api_client.get_domain_id.return_value = ("domain-uuid", None)
        api_client.list_detected_links.return_value = (
            [
                {"id": "id-1", "url": "https://example.com/path"},  # 100% giống
                {"id": "id-2", "url": "https://other.com/xxx"},
            ],
            None,
        )
        detect_tool.api_client = api_client
        
        upload_tool.execute.return_value = (True, None)
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler,
        )
        
        result = agent.process_image(
            image_path=temp_image_file,
            match_name="Test Match",
            sport_id="sport-uuid",
        )
        
        assert result["success"] is True
        assert result["detected_link_id"] == "id-1"
    
    def test_process_image_rescue_agent(self, mock_tools, temp_image_file, monkeypatch):
        """Rescue flow: similarity < 0.85, dùng agent (choose_best_detected_link)."""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        ocr_url = "https://example.com/partial"
        url_tool.execute.return_value = (ocr_url, None)
        detect_tool.execute.return_value = (None, None)
        
        api_client = Mock()
        api_client.get_domain_id.return_value = ("domain-uuid", None)
        api_client.list_detected_links.return_value = (
            [
                {"id": "id-1", "url": "https://example.com/full-path"},
                {"id": "id-2", "url": "https://other.com/xxx"},
            ],
            None,
        )
        detect_tool.api_client = api_client
        
        # Patch similarity helper để luôn trả score thấp (<0.85) -> buộc dùng agent
        monkeypatch.setattr(
            "app.agents.image_processing_agent.ImageProcessingAgent._find_best_similarity_match",
            lambda self, ocr_url, candidates: (None, None, 0.5),
        )
        
        # choose_best_detected_link trả về 1 ID
        url_tool.choose_best_detected_link.return_value = (
            "id-1",
            "https://example.com/full-path",
            0.95,
        )
        
        upload_tool.execute.return_value = (True, None)
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler,
        )
        
        result = agent.process_image(
            image_path=temp_image_file,
            match_name="Test Match",
            sport_id="sport-uuid",
        )
        
        assert result["success"] is True
        assert result["detected_link_id"] == "id-1"
    
    def test_process_image_upload_error(self, mock_tools, temp_image_file):
        """Test image processing with upload error"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.return_value = ("https://example.com", None)
        detect_tool.execute.return_value = (456, None)
        upload_tool.execute.return_value = (False, "Upload failed")
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        result = agent.process_image(
            image_path=temp_image_file,
            match_name="Test Match",
            sport_id=123
        )
        
        assert result["success"] is False
        assert result["error_type"] == "upload_error"
        assert "Upload failed" in result["error"]
    
    def test_process_images_batch_one_image(self, mock_tools, temp_image_file):
        """Test processing batch with 1 image"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.return_value = ("https://example.com", None)
        detect_tool.execute.return_value = ("uuid-1", None)
        upload_tool.execute.return_value = (True, None)
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        batch = [
            {
                "id": 1,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            }
        ]
        
        results = agent.process_images_batch(batch)
        
        assert len(results) == 1
        assert results[0]["image_id"] == 1
        assert results[0]["success"] is True
        assert results[0]["url"] == "https://example.com"
        assert results[0]["detected_link_id"] == "uuid-1"
    
    def test_process_images_batch_two_images_both_success(self, mock_tools, temp_image_file):
        """Test processing batch with 2 images - both succeed"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        # Setup mocks - both images succeed with different URLs / link IDs
        url_tool.execute.side_effect = [
            ("https://example1.com", None),
            ("https://example2.com", None)
        ]
        detect_tool.execute.side_effect = [
            ("uuid-1", None),
            ("uuid-2", None)
        ]
        upload_tool.execute.side_effect = [
            (True, None),
            (True, None)
        ]
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        batch = [
            {
                "id": 1,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            },
            {
                "id": 2,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            }
        ]
        
        results = agent.process_images_batch(batch)
        
        assert len(results) == 2
        assert results[0]["image_id"] == 1
        assert results[1]["image_id"] == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is True
        assert results[0]["url"] == "https://example1.com"
        assert results[1]["url"] == "https://example2.com"
        assert results[0]["detected_link_id"] == "uuid-1"
        assert results[1]["detected_link_id"] == "uuid-2"
    
    def test_process_images_batch_one_fail_extract_one_success(self, mock_tools, temp_image_file):
        """Test batch: 1 image fails extraction, 1 succeeds"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.side_effect = [
            (None, "Extraction failed"),
            ("https://example2.com", None)
        ]
        detect_tool.execute.return_value = ("uuid-2", None)
        upload_tool.execute.return_value = (True, None)
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        batch = [
            {
                "id": 1,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            },
            {
                "id": 2,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            }
        ]
        
        results = agent.process_images_batch(batch)
        
        assert len(results) == 2
        assert results[0]["image_id"] == 1
        assert results[1]["image_id"] == 2
        assert results[0]["success"] is False
        assert results[0]["error_type"] == "extract_error"
        assert results[1]["success"] is True
        assert results[1]["url"] == "https://example2.com"
    
    def test_process_images_batch_one_fail_detect_one_success(self, mock_tools, temp_image_file):
        """Test batch: 1 image fails detection, 1 succeeds"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.side_effect = [
            ("https://example1.com", None),
            ("https://example2.com", None)
        ]
        detect_tool.execute.side_effect = [
            (None, "Detection failed"),
            ("uuid-2", None)
        ]
        upload_tool.execute.return_value = (True, None)
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        batch = [
            {
                "id": 1,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            },
            {
                "id": 2,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            }
        ]
        
        results = agent.process_images_batch(batch)
        
        assert len(results) == 2
        assert results[0]["image_id"] == 1
        assert results[1]["image_id"] == 2
        assert results[0]["success"] is False
        assert results[0]["error_type"] == "detect_error"
        assert results[0]["url"] == "https://example1.com"  # URL was extracted
        assert results[1]["success"] is True
        assert results[1]["url"] == "https://example2.com"
    
    def test_process_images_batch_one_fail_upload_one_success(self, mock_tools, temp_image_file):
        """Test batch: 1 image fails upload, 1 succeeds"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.side_effect = [
            ("https://example1.com", None),
            ("https://example2.com", None)
        ]
        detect_tool.execute.side_effect = [
            ("uuid-1", None),
            ("uuid-2", None)
        ]
        upload_tool.execute.side_effect = [
            (False, "Upload failed"),
            (True, None)
        ]
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        batch = [
            {
                "id": 1,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            },
            {
                "id": 2,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            }
        ]
        
        results = agent.process_images_batch(batch)
        
        assert len(results) == 2
        assert results[0]["image_id"] == 1
        assert results[1]["image_id"] == 2
        assert results[0]["success"] is False
        assert results[0]["error_type"] == "upload_error"
        assert results[0]["url"] == "https://example1.com"
        assert results[1]["success"] is True
        assert results[1]["url"] == "https://example2.com"
    
    def test_process_images_batch_both_fail(self, mock_tools, temp_image_file):
        """Test batch: both images fail"""
        url_tool, detect_tool, upload_tool, error_handler = mock_tools
        
        url_tool.execute.side_effect = [
            (None, "Extraction failed 1"),
            (None, "Extraction failed 2")
        ]
        
        agent = ImageProcessingAgent(
            url_extractor_tool=url_tool,
            detect_link_tool=detect_tool,
            upload_image_tool=upload_tool,
            error_handler=error_handler
        )
        
        batch = [
            {
                "id": 1,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            },
            {
                "id": 2,
                "image_path": temp_image_file,
                "match_name": "Test Match",
                "sport_id": 123
            }
        ]
        
        results = agent.process_images_batch(batch)
        
        assert len(results) == 2
        assert results[0]["image_id"] == 1
        assert results[1]["image_id"] == 2
        assert results[0]["success"] is False
        assert results[1]["success"] is False
        assert results[0]["error_type"] == "extract_error"
        assert results[1]["error_type"] == "extract_error"