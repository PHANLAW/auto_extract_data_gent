"""
Unit tests for Sport API client
"""

import pytest
import requests
from unittest.mock import Mock, patch
from app.utils.sport_api import SportAPIClient


class TestSportAPIClient:
    """Test Sport API client"""
    
    def test_get_sport_id_success(self, monkeypatch):
        """Test successful sport ID retrieval with new auth + league/sport flow."""

        client = SportAPIClient(base_url="https://test.com", username="u", password="p")

        # Bỏ qua login thực, coi như đã có token
        client.access_token = "token"
        client.headers["Authorization"] = "Bearer token"

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self._data = data
                    self.text = ""

                def json(self):
                    return self._data

            if path == "/api/v1/leagues/":
                # Trả về league_id
                return Resp(200, {"data": [{"id": "league-uuid"}]})
            elif path == "/api/v1/sports/":
                # Trả về sport_id
                return Resp(200, {"data": [{"id": "sport-uuid"}]})
            return Resp(500, {})

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        sport_id, error = client.get_sport_id("Match", "2026-01-02 00:30", "PL 25_26")

        assert error is None
        assert sport_id == "sport-uuid"
    
    def test_get_sport_id_api_error(self):
        """Test get_sport_id when league API fails."""
        client = SportAPIClient(base_url="https://test.com", username="u", password="p")

        client.access_token = "token"
        client.headers["Authorization"] = "Bearer token"

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code, text):
                    self.status_code = status_code
                    self.text = text

                def json(self):
                    return {}

            if path == "/api/v1/leagues/":
                # Simulate 500 from league API
                return Resp(500, "Internal Server Error")

            return Resp(500, "Unexpected")

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        sport_id, error = client.get_sport_id("Match", "2026-01-02 00:30", "PL")

        assert sport_id is None
        assert error is not None
        assert "API error 500" in error
    
    def test_detect_link_success(self):
        """Test successful link detection using new check_exists logic."""
        client = SportAPIClient(base_url="https://test.com", username="u", password="p")

        client.access_token = "token"
        client.headers["Authorization"] = "Bearer token"

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self._data = data
                    self.text = ""

                def json(self):
                    return self._data

            # Chỉ cần trả về 1 ID cho URL gốc
            return Resp(200, {"detected-id": True})

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        link_id, error = client.detect_link("https://example.com", "sport-uuid")

        assert error is None
        assert link_id == "detected-id"
    
    def test_upload_image_success(self, temp_image_file, monkeypatch):
        """Test successful image upload with new auth + multipart flow."""
        client = SportAPIClient(base_url="https://test.com", username="u", password="p")

        # Giả lập đã login xong
        client.access_token = "token"
        client.headers["Authorization"] = "Bearer token"

        def fake_post(url, files=None, data=None, headers=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code):
                    self.status_code = status_code
                    self.text = ""

            # Lần đầu trả 201 luôn
            return Resp(201)

        monkeypatch.setattr("requests.post", fake_post)

        success, error = client.upload_image(temp_image_file, "detected-id")

        assert success is True
        assert error is None

    def test_upload_image_accepted_async(self, temp_image_file, monkeypatch):
        """Test upload image returns success for async 202 Accepted response."""
        client = SportAPIClient(base_url="https://test.com", username="u", password="p")

        client.access_token = "token"
        client.headers["Authorization"] = "Bearer token"

        def fake_post(url, files=None, data=None, headers=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self):
                    self.status_code = 202
                    self.text = (
                        '{"status":"accepted","command_id":"cmd-123",'
                        '"correlation_id":"corr-456"}'
                    )

                def json(self):
                    return {
                        "status": "accepted",
                        "command_id": "cmd-123",
                        "correlation_id": "corr-456",
                    }

            return Resp()

        monkeypatch.setattr("requests.post", fake_post)

        success, error = client.upload_image(temp_image_file, "detected-id")

        assert success is True
        assert error is None
    
    def test_upload_image_file_not_found(self):
        """Test upload with non-existent file"""
        client = SportAPIClient(base_url="https://test.com")
        success, error = client.upload_image("nonexistent.png", 456)
        
        assert success is False
        assert "not found" in error.lower()

    # ==========================
    # New tests for check_exists
    # ==========================

    def test_check_exists_original_only(self):
        """Nếu chỉ URL gốc có detected_link_id, phải trả về ID đó."""
        client = SportAPIClient(base_url="https://test.com")

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            # Giả lập response cho từng URL
            class Resp:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self._data = data

                def json(self):
                    return self._data

                text = ""

            url = params["url"]
            if url == "https://example.com/path":
                # Chỉ URL gốc có detected_link_id
                return Resp(200, {"id-original": True})
            elif url == "https://www.example.com/path":
                # Bản www không có
                return Resp(200, {})
            return Resp(200, {})

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        detected_link_id, error = client.check_exists("https://example.com/path", "sport-uuid")

        assert error is None
        assert detected_link_id == "id-original"

    def test_check_exists_original_and_www_same_id(self):
        """Nếu cả URL gốc và www đều trỏ tới cùng một ID, vẫn dùng được."""
        client = SportAPIClient(base_url="https://test.com")

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self._data = data

                def json(self):
                    return self._data

                text = ""

            # Cả 2 biến thể đều trả về cùng một ID
            return Resp(200, {"same-id": True})

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        detected_link_id, error = client.check_exists("https://example.com/path", "sport-uuid")

        assert error is None
        assert detected_link_id == "same-id"

    def test_check_exists_ambiguous_ids(self):
        """Nếu URL gốc và www trả về 2 ID khác nhau, phải báo lỗi ambiguous."""
        client = SportAPIClient(base_url="https://test.com")

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self._data = data

                def json(self):
                    return self._data

                text = ""

            url = params["url"]
            if url.startswith("https://example.com"):
                return Resp(200, {"id-original": True})
            elif url.startswith("https://www.example.com"):
                return Resp(200, {"id-www": True})
            return Resp(200, {})

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        detected_link_id, error = client.check_exists("https://example.com/path", "sport-uuid")

        assert detected_link_id is None
        assert error is not None
        assert "Ambiguous detected_link_id" in error

    def test_check_exists_no_match(self):
        """Nếu cả URL gốc, www và bản thêm '/' đều không có detected_link_id, trả về (None, None)."""
        client = SportAPIClient(base_url="https://test.com")

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self._data = data

                def json(self):
                    return self._data

                text = ""

            return Resp(200, {})

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        detected_link_id, error = client.check_exists("https://example.com/path", "sport-uuid")

        assert detected_link_id is None
        assert error is None

    def test_check_exists_trailing_slash_variant(self):
        """Nếu chỉ biến thể có '/' cuối cùng có detected_link_id, phải trả về ID đó."""
        client = SportAPIClient(base_url="https://test.com")

        def fake_make_request(method, path, params=None, timeout=None, **kwargs):
            class Resp:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self._data = data

                def json(self):
                    return self._data

                text = ""

            url = params["url"]
            # Lần 1: URL gốc và www không có
            if url in ("https://example.com/path", "https://www.example.com/path"):
                return Resp(200, {})
            # Lần 2: chỉ bản có '/' mới có detected_link_id
            if url == "https://example.com/path/":
                return Resp(200, {"id-slash": True})
            if url == "https://www.example.com/path/":
                return Resp(200, {})
            return Resp(200, {})

        client._make_request = fake_make_request  # type: ignore[attr-defined]

        detected_link_id, error = client.check_exists("https://example.com/path", "sport-uuid")

        assert error is None
        assert detected_link_id == "id-slash"
