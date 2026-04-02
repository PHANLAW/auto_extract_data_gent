"""
Processing Manager: Manage auto-processing state and trigger processing
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime
from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()


class ProcessingManager:
    """Manage processing state and auto-processing"""
    
    def __init__(self):
        """Initialize processing manager"""
        self.state_file = "processing_state.json"
    
    def load_state(self) -> Dict:
        """Load processing state"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading processing state: {e}")
                return {"blob_auto_enabled": False}
        return {"blob_auto_enabled": False}
    
    def save_state(self, state: Dict):
        """Save processing state"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving processing state: {e}")
    
    def set_blob_auto_enabled(self, enabled: bool) -> bool:
        """
        Set blob auto-processing enabled state
        
        Returns:
            True if successful, False if invalid mode
        """
        if settings.DATA_SOURCE_MODE != "blob_storage":
            return False
        
        state = self.load_state()
        state["blob_auto_enabled"] = enabled
        state["last_updated"] = datetime.now().isoformat()
        self.save_state(state)
        logger.info(f"Blob auto-processing set to: {enabled}")
        return True
    
    def is_blob_auto_enabled(self) -> bool:
        """Check if blob auto-processing is enabled"""
        if settings.DATA_SOURCE_MODE != "blob_storage":
            return False
        state = self.load_state()
        return state.get("blob_auto_enabled", False)
