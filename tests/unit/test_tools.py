"""
Unit tests for tools
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.tools.base import BaseTool
from app.tools.url_extractor_tool import URLExtractorTool
from app.tools.api_tools import DetectLinkTool, UploadImageTool
from app.tools.tool_manager import ToolManager


class TestBaseTool:
    """Test base tool interface"""
    
    def test_base_tool_abstract(self):
        """Test that BaseTool is abstract"""
        with pytest.raises(TypeError):
            BaseTool(name="test", description="test")
    
    def test_tool_schema(self):
        """Test tool schema generation"""
        class TestTool(BaseTool):
            def execute(self, **kwargs):
                return None, None
        
        tool = TestTool(name="test_tool", description="Test tool")
        schema = tool.get_schema()
        
        assert schema["name"] == "test_tool"
        assert schema["description"] == "Test tool"


class TestURLExtractorTool:
    """Test URL extractor tool"""
    
    def test_validate_missing_image_path(self, mock_azure_client):
        """Test validation with missing image path"""
        tool = URLExtractorTool(mock_azure_client)
        is_valid, error = tool.validate()
        
        assert is_valid is False
        assert "required" in error.lower()
    
    def test_validate_invalid_image_path(self, mock_azure_client):
        """Test validation with invalid image path"""
        tool = URLExtractorTool(mock_azure_client)
        is_valid, error = tool.validate(image_path="nonexistent.png")
        
        assert is_valid is False
        assert "not found" in error.lower()
    
    def test_extract_url_uses_gcv_first(self, mock_azure_client, temp_image_file, monkeypatch):
        """Nếu GCV trả về URL, execute() phải dùng luôn mà không gọi Azure OpenAI."""
        tool = URLExtractorTool(mock_azure_client)
        # Bỏ crop để không dính tới cv2 trong unit test
        tool.use_crop = False

        # GCV trả về URL trước
        monkeypatch.setattr(
            tool,
            "extract_url_with_gcv",
            lambda image_path: "http://example.com/path",
        )

        # Azure client không được gọi
        mock_azure_client.chat.completions.create.assert_not_called()

        url, error = tool.execute(image_path=temp_image_file)

        assert error is None
        assert url == "http://example.com/path"
        mock_azure_client.chat.completions.create.assert_not_called()

    def test_extract_url_fallback_to_azure(self, mock_azure_client, temp_image_file, monkeypatch):
        """Nếu GCV không trả URL, execute() phải fallback sang Azure OpenAI."""
        tool = URLExtractorTool(mock_azure_client)
        tool.use_crop = False

        # GCV fail
        monkeypatch.setattr(tool, "extract_url_with_gcv", lambda image_path: None)

        # Mock Azure response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "https://azure-example.com/path"
        mock_response.choices = [mock_choice]
        mock_azure_client.chat.completions.create.return_value = mock_response

        url, error = tool.execute(image_path=temp_image_file)

        assert error is None
        assert url == "https://azure-example.com/path"
        mock_azure_client.chat.completions.create.assert_called_once()

    def test_extract_url_with_gcv_insecure_no_scheme(self, mock_azure_client, tmp_path, monkeypatch):
        """GCV: có 'Không bảo mật' và URL không có scheme -> thêm http://."""
        tool = URLExtractorTool(mock_azure_client)

        # Tạo file tạm cho GCV đọc (nội dung không quan trọng vì ta mock response)
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"dummy")

        class FakeFullText:
            text = "Không bảo mật\n demnay.agency/truc-tiep"

        class FakeError:
            message = ""

        class FakeResponse:
            full_text_annotation = FakeFullText()
            error = FakeError()

        class FakeClient:
            def document_text_detection(self, image):
                return FakeResponse()

        monkeypatch.setattr(
            tool, "_get_gcv_client", lambda: FakeClient()
        )

        url = tool.extract_url_with_gcv(str(img_path))

        assert url == "http://demnay.agency/truc-tiep"

    def test_extract_url_with_gcv_secure_no_scheme(self, mock_azure_client, tmp_path, monkeypatch):
        """GCV: không có cảnh báo bảo mật và URL không scheme -> thêm https://."""
        tool = URLExtractorTool(mock_azure_client)

        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"dummy")

        class FakeFullText:
            text = "Trang web an toàn\n ve.bo8.hair/truc-tiep"

        class FakeError:
            message = ""

        class FakeResponse:
            full_text_annotation = FakeFullText()
            error = FakeError()

        class FakeClient:
            def document_text_detection(self, image):
                return FakeResponse()

        monkeypatch.setattr(
            tool, "_get_gcv_client", lambda: FakeClient()
        )

        url = tool.extract_url_with_gcv(str(img_path))

        assert url == "https://ve.bo8.hair/truc-tiep"

    def test_extract_url_with_gcv_insecure_https_scheme(self, mock_azure_client, tmp_path, monkeypatch):
        """GCV: có cảnh báo bảo mật và URL đã có https:// -> phải ép về http://."""
        tool = URLExtractorTool(mock_azure_client)

        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"dummy")

        class FakeFullText:
            text = "Not secure\nhttps://insecure.example.com/path"

        class FakeError:
            message = ""

        class FakeResponse:
            full_text_annotation = FakeFullText()
            error = FakeError()

        class FakeClient:
            def document_text_detection(self, image):
                return FakeResponse()

        monkeypatch.setattr(
            tool, "_get_gcv_client", lambda: FakeClient()
        )

        url = tool.extract_url_with_gcv(str(img_path))

        assert url == "http://insecure.example.com/path"


class TestDetectLinkTool:
    """Test detect link tool"""
    
    def test_validate_missing_params(self, mock_sport_api_client):
        """Test validation with missing parameters"""
        tool = DetectLinkTool(mock_sport_api_client)
        
        is_valid, error = tool.validate()
        assert is_valid is False
        
        is_valid, error = tool.validate(url="https://test.com")
        assert is_valid is False
    
    def test_execute_success(self, mock_sport_api_client):
        """Test successful link detection"""
        tool = DetectLinkTool(mock_sport_api_client)
        link_id, error = tool.execute(url="https://test.com", sport_id="sport-uuid")
        
        assert link_id == "uuid-456"
        assert error is None


class TestUploadImageTool:
    """Test upload image tool"""
    
    def test_validate_missing_params(self, mock_sport_api_client, temp_image_file):
        """Test validation with missing parameters"""
        tool = UploadImageTool(mock_sport_api_client)
        
        is_valid, error = tool.validate(image_path=temp_image_file)
        assert is_valid is False
    
    def test_execute_success(self, mock_sport_api_client, temp_image_file):
        """Test successful image upload"""
        tool = UploadImageTool(mock_sport_api_client)
        success, error = tool.execute(
            image_path=temp_image_file,
            detected_link_id="uuid-456"
        )
        
        assert success is True
        assert error is None


class TestToolManager:
    """Test tool manager"""
    
    def test_register_tool(self):
        """Test tool registration"""
        manager = ToolManager()
        
        class TestTool(BaseTool):
            def execute(self, **kwargs):
                return None, None
        
        tool = TestTool(name="test", description="Test")
        manager.register_tool(tool)
        
        assert "test" in manager.list_tools()
        assert manager.get_tool("test") is tool
    
    def test_get_nonexistent_tool(self):
        """Test getting non-existent tool"""
        manager = ToolManager()
        tool = manager.get_tool("nonexistent")
        
        assert tool is None
    
    def test_execute_tool(self):
        """Test tool execution"""
        manager = ToolManager()
        
        class TestTool(BaseTool):
            def execute(self, **kwargs):
                return "result", None
        
        tool = TestTool(name="test", description="Test")
        manager.register_tool(tool)
        
        result, error = manager.execute_tool("test", param1="value1")
        
        assert result == "result"
        assert error is None
