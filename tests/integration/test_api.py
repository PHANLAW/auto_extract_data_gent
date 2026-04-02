"""
Integration tests for API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_parse_folder(self, client, sample_folder_name):
        """Test parse folder endpoint"""
        response = client.post(
            "/api/v1/parse-folder",
            json={"folder_name": sample_folder_name}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["match_name"] == "Crystal Palace - Fulham"
    
    def test_parse_folder_invalid(self, client):
        """Test parse folder with invalid name"""
        response = client.post(
            "/api/v1/parse-folder",
            json={"folder_name": "Invalid"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
    
    def test_list_tools(self, client):
        """Test list tools endpoint"""
        response = client.get("/api/v1/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
