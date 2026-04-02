"""
API Tools: Tools for interacting with Sport API
"""

import requests
from typing import Optional, Tuple, Dict
from app.tools.base import BaseTool
from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()


class DetectLinkTool(BaseTool):
    """Tool for detecting links via API"""
    
    def __init__(self, api_client):
        """
        Initialize detect link tool
        
        Args:
            api_client: SportAPIClient instance
        """
        super().__init__(
            name="detect_link",
            description="Detect link and get detected_link_id from API"
        )
        self.api_client = api_client
    
    def validate(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Validate inputs"""
        url = kwargs.get("url")
        sport_id = kwargs.get("sport_id")
        
        if not url:
            return False, "url is required"
        if not sport_id:
            return False, "sport_id is required"
        if not isinstance(sport_id, str):
            return False, "sport_id must be a UUID string"
        
        return True, None
    
    def execute(self, **kwargs) -> Tuple[Optional[str], Optional[str]]:
        """
        Check if detected link exists and get detected_link_id
        
        Args:
            url: URL extracted from image
            sport_id: Sport ID (UUID string)
        
        Returns:
            Tuple of (detected_link_id, error_message)
            detected_link_id is UUID string if exists, None if not exists
        """
        url = kwargs.get("url")
        sport_id = kwargs.get("sport_id")
        
        # Validate
        is_valid, error = self.validate(**kwargs)
        if not is_valid:
            return None, error
        
        try:
            detected_link_id, api_error = self.api_client.check_exists(url, sport_id)
            
            if api_error:
                logger.warning(f"Check exists failed: {api_error}")
                return None, api_error
            
            if not detected_link_id:
                # Not found, but not an error - return None to indicate not exists
                logger.info(f"Detected link does not exist for URL: {url}")
                return None, None
            
            logger.info(f"Detected link ID: {detected_link_id}")
            return detected_link_id, None
            
        except Exception as e:
            logger.error(f"Error checking detected link: {e}")
            return None, f"Error checking detected link: {str(e)}"
    
    def get_schema(self) -> Dict:
        """Get tool schema"""
        schema = super().get_schema()
        schema["parameters"] = {
            "url": {
                "type": "string",
                "description": "URL extracted from image",
                "required": True
            },
            "sport_id": {
                "type": "string",
                "description": "Sport ID (UUID string)",
                "required": True
            }
        }
        return schema


class UploadImageTool(BaseTool):
    """Tool for uploading images via API"""
    
    def __init__(self, api_client):
        """
        Initialize upload image tool
        
        Args:
            api_client: SportAPIClient instance
        """
        super().__init__(
            name="upload_image",
            description="Upload image with detected_link_id"
        )
        self.api_client = api_client
    
    def validate(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Validate inputs"""
        import os
        
        image_path = kwargs.get("image_path")
        detected_link_id = kwargs.get("detected_link_id")
        
        if not image_path:
            return False, "image_path is required"
        if not os.path.exists(image_path):
            return False, f"Image file not found: {image_path}"
        if not detected_link_id:
            return False, "detected_link_id is required"
        if not isinstance(detected_link_id, str):
            return False, "detected_link_id must be a UUID string"
        
        return True, None
    
    def execute(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Upload image
        
        Args:
            image_path: Path to image file
            detected_link_id: Detected link ID (UUID string)
        
        Returns:
            Tuple of (success, error_message)
        """
        image_path = kwargs.get("image_path")
        detected_link_id = kwargs.get("detected_link_id")
        url = kwargs.get("url")  # Optional: original URL, used to derive domain for filename
        
        # Validate
        is_valid, error = self.validate(**kwargs)
        if not is_valid:
            return False, error
        
        try:
            # Pass URL (if provided) so API client can generate unique filename using detected_link_id + domain
            success, upload_error = self.api_client.upload_image(
                image_path=image_path,
                detected_link_id=detected_link_id,
                url=url
            )
            
            if not success:
                logger.warning(f"Upload failed: {upload_error}")
                return False, upload_error
            
            logger.info(f"Image uploaded successfully: {image_path}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return False, f"Error uploading image: {str(e)}"
    
    def get_schema(self) -> Dict:
        """Get tool schema"""
        schema = super().get_schema()
        schema["parameters"] = {
            "image_path": {
                "type": "string",
                "description": "Path to the image file",
                "required": True
            },
            "detected_link_id": {
                "type": "string",
                "description": "Detected link ID (UUID string)",
                "required": True
            }
        }
        return schema
