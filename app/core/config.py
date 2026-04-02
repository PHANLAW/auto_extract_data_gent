"""
Configuration Management
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Image Processing Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o-mini"
    
    # Sport API
    SPORT_API_BASE_URL: str = os.getenv("SPORT_API_BASE_URL", "")
    SPORT_API_KEY: Optional[str] = os.getenv("SPORT_API_KEY", None)
    SPORT_API_USERNAME: Optional[str] = os.getenv("SPORT_API_USERNAME", None)
    SPORT_API_PASSWORD: Optional[str] = os.getenv("SPORT_API_PASSWORD", None)
    
    # Processing
    USE_CROP: bool = True  # Crop top region (address bar) for URL extraction
    CROP_RATIO: float = 0.15  # Crop top ~15% of image (full width) where address bar is located
    IMAGE_EXTENSIONS: str = ".png,.jpg,.jpeg,.bmp,.gif"

    # Google Cloud Vision
    GCV_SERVICE_ACCOUNT_FILE: str = "service-account.json"  # Path to service account JSON for Vision API
    
    # Error Handling
    RETRY_FILE: str = "retry_failed.json"
    RETRY_FILE_FORMAT: str = "json"  # json or csv
    WARNING_MATCHES_FILE: str = "warning_matches.json"  # File for AI-guessed matches (similarity/agent)
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Data Source
    DATA_SOURCE_MODE: str = "local"  # local or blob_storage
    LOCAL_DATA_PATH: str = "data"
    
    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING", None)
    AZURE_BLOB_CONTAINER_NAME: str = "image-folders"
    AZURE_BLOB_PREFIX: str = ""
    AZURE_BLOB_DOWNLOAD_PATH: str = "temp_blob_downloads"
    
    # Auto Processing
    AUTO_PROCESS_ENABLED: bool = False
    AUTO_PROCESS_INTERVAL: int = 300  # seconds
    AUTO_PROCESS_CONCURRENT_FOLDERS: int = 3
    AUTO_PROCESS_CONCURRENT_IMAGES: int = 5
    
    # Rate Limiting (to avoid Azure OpenAI 429 errors)
    AZURE_OPENAI_REQUEST_DELAY: float = 2.5  # Delay in seconds between requests (increased to reduce 429 errors)
    AZURE_OPENAI_RETRY_DELAY: float = 5.0  # Additional delay after 429 error (seconds)
    
    # Tracker
    TRACKER_STATE_FILE: str = "tracker_state.json"
    TRACKER_ONLY_NEW: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
