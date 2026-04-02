"""
Unit tests for Configuration
"""

import pytest
import os
from unittest.mock import patch
from app.core.config import Settings, get_settings


class TestSettings:
    """Test Settings configuration"""
    
    def test_default_values(self):
        """Test default configuration values"""
        settings = Settings()
        
        assert settings.APP_NAME == "Image Processing Agent"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG is False
        assert settings.USE_CROP is True
        assert settings.CROP_RATIO == 0.13
    
    @patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "SPORT_API_BASE_URL": "https://test-api.com"
    })
    def test_load_from_env(self):
        """Test loading from environment variables"""
        settings = Settings()
        
        assert settings.AZURE_OPENAI_API_KEY == "test-key"
        assert settings.AZURE_OPENAI_ENDPOINT == "https://test.openai.azure.com"
        assert settings.SPORT_API_BASE_URL == "https://test-api.com"
    
    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_blob_storage_config(self):
        """Test blob storage configuration"""
        settings = Settings()
        
        assert hasattr(settings, "DATA_SOURCE_MODE")
        assert hasattr(settings, "AZURE_STORAGE_CONNECTION_STRING")
        assert hasattr(settings, "AZURE_BLOB_CONTAINER_NAME")
        assert hasattr(settings, "AUTO_PROCESS_ENABLED")
