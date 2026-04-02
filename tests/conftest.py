"""
Pytest configuration and fixtures
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from openai import AzureOpenAI

# Set test environment variables
os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com"
os.environ["SPORT_API_BASE_URL"] = "https://test-api.com"
os.environ["SPORT_API_KEY"] = "test-api-key"
os.environ["DATA_SOURCE_MODE"] = "local"
os.environ["LOCAL_DATA_PATH"] = "data"


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_image_file(temp_dir):
    """Create temporary image file"""
    image_path = Path(temp_dir) / "test_image.png"
    # Create a minimal PNG file
    image_path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
    return str(image_path)


@pytest.fixture
def mock_azure_client():
    """Mock Azure OpenAI client"""
    mock_client = Mock(spec=AzureOpenAI)
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "https://example.com/test"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_sport_api_client():
    """Mock Sport API client"""
    mock_client = Mock()
    # get_sport_id now returns UUID string
    mock_client.get_sport_id.return_value = ("sport-uuid", None)
    # New API surface: check_exists (used by DetectLinkTool)
    mock_client.check_exists.return_value = ("uuid-456", None)
    mock_client.get_domain_id.return_value = ("domain-uuid", None)
    mock_client.list_detected_links.return_value = (
        [
            {"id": "uuid-1", "url": "https://candidate1.example.com"},
            {"id": "uuid-2", "url": "https://candidate2.example.com"},
        ],
        None,
    )
    # Backward-compat / other usages
    mock_client.detect_link.return_value = ("uuid-456", None)
    mock_client.upload_image.return_value = (True, None)
    return mock_client


@pytest.fixture
def sample_folder_name():
    """Sample folder name for testing"""
    return "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"


@pytest.fixture
def sample_parsed_folder():
    """Sample parsed folder data"""
    return {
        "start_time": "2026-01-02 00:30",
        "league": "PL 25_26",
        "match_name": "Crystal Palace - Fulham",
        "original_start_time": "02.01.26 00:30"
    }


@pytest.fixture
def retry_file_path(temp_dir):
    """Path to retry file"""
    return str(Path(temp_dir) / "retry_failed.json")


@pytest.fixture
def reset_agent_manager():
    """Reset agent manager singleton for testing"""
    from app.core.agent_manager import AgentManager
    AgentManager._instance = None
    AgentManager._agent = None
    AgentManager._azure_client = None
    AgentManager._api_client = None
    AgentManager._error_handler = None
    yield
    # Cleanup
    AgentManager._instance = None
    AgentManager._agent = None
    AgentManager._azure_client = None
    AgentManager._api_client = None
    AgentManager._error_handler = None


@pytest.fixture
def sample_data_structure(temp_dir):
    """Create sample data structure"""
    from tests.fixtures.sample_data import create_sample_folder_structure
    return create_sample_folder_structure(temp_dir)
