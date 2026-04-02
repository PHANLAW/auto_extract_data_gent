"""
Unit tests for error handler
"""

import pytest
import json
import os
from pathlib import Path
from app.utils.error_handler import ErrorHandler


class TestErrorHandler:
    """Test error handler"""
    
    def test_write_failed_url_json(self, temp_dir):
        """Test writing failed URL to JSON file"""
        retry_file = str(Path(temp_dir) / "retry.json")
        handler = ErrorHandler(retry_file=retry_file, file_format="json")
        
        handler.write_failed_url(
            match_name="Test Match",
            image_name="test.png",
            url="https://example.com",
            error="Test error"
        )
        
        assert os.path.exists(retry_file)
        
        with open(retry_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["error_type"] == "detect_error"
        assert data[0]["match_name"] == "Test Match"
        assert data[0]["image_name"] == "test.png"
        assert data[0]["url"] == "https://example.com"
        assert data[0]["error"] == "Test error"
    
    def test_write_failed_url_csv(self, temp_dir):
        """Test writing failed URL to CSV file"""
        retry_file = str(Path(temp_dir) / "retry.csv")
        handler = ErrorHandler(retry_file=retry_file, file_format="csv")
        
        handler.write_failed_url(
            match_name="Test Match",
            image_name="test.png",
            url="https://example.com",
            error="Test error"
        )
        
        assert os.path.exists(retry_file)
        
        with open(retry_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        assert len(lines) == 2  # Header + 1 data row
        assert "Test Match" in lines[1]
    
    def test_read_failed_urls_json(self, temp_dir):
        """Test reading failed URLs from JSON file"""
        retry_file = str(Path(temp_dir) / "retry.json")
        handler = ErrorHandler(retry_file=retry_file, file_format="json")
        
        # Write some data
        handler.write_failed_url("Match 1", "img1.png", "https://url1.com", "Error 1")
        handler.write_failed_url("Match 2", "img2.png", "https://url2.com", "Error 2")
        
        # Read back
        failed_urls = handler.read_failed_urls()
        
        assert len(failed_urls) == 2
        assert failed_urls[0]["match_name"] == "Match 1"
        assert failed_urls[1]["match_name"] == "Match 2"
    
    def test_read_failed_urls_empty(self, temp_dir):
        """Test reading from empty file"""
        retry_file = str(Path(temp_dir) / "retry.json")
        handler = ErrorHandler(retry_file=retry_file, file_format="json")
        
        failed_urls = handler.read_failed_urls()
        assert failed_urls == []
    
    def test_write_failed_extraction(self, temp_dir):
        """Test writing failed URL extraction"""
        retry_file = str(Path(temp_dir) / "retry.json")
        handler = ErrorHandler(retry_file=retry_file, file_format="json")
        
        handler.write_failed_extraction(
            match_name="Test Match",
            image_name="test.png",
            error="Cannot extract URL"
        )
        
        failed_urls = handler.read_failed_urls()
        assert len(failed_urls) == 1
        assert failed_urls[0]["error_type"] == "extract_error"
        assert failed_urls[0]["match_name"] == "Test Match"
        assert failed_urls[0]["image_name"] == "test.png"
        assert failed_urls[0]["url"] is None
        assert failed_urls[0]["error"] == "Cannot extract URL"
    
    def test_write_failed_sport_id(self, temp_dir):
        """Test writing failed sport_id lookup"""
        retry_file = str(Path(temp_dir) / "retry.json")
        handler = ErrorHandler(retry_file=retry_file, file_format="json")
        
        handler.write_failed_sport_id(
            folder_name="02.01.26 00:30 PL 25_26 Test Match",
            match_name="Test Match",
            league="PL",
            start_time="2026-01-02 00:30",
            error="API error"
        )
        
        failed_urls = handler.read_failed_urls()
        assert len(failed_urls) == 1
        assert failed_urls[0]["error_type"] == "sport_id_error"
        assert failed_urls[0]["match_name"] == "Test Match"
        assert failed_urls[0]["image_name"] is None
        assert failed_urls[0]["url"] is None
        assert failed_urls[0]["folder_name"] == "02.01.26 00:30 PL 25_26 Test Match"
        assert "Cannot get sport_id" in failed_urls[0]["error"]
