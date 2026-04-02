"""
Local Folder Tracker: Track and process folders from local data directory
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime
from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()


class LocalFolderTracker:
    """Track folders in local data directory"""
    
    def __init__(self):
        """Initialize local folder tracker"""
        self.data_path = Path(settings.LOCAL_DATA_PATH)
        self.state_file = settings.TRACKER_STATE_FILE
        self.data_path.mkdir(parents=True, exist_ok=True)
    
    def load_state(self) -> Dict:
        """Load tracker state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    # Ensure local_processed_folders exists
                    if "local_processed_folders" not in state:
                        state["local_processed_folders"] = []
                    return state
            except Exception as e:
                logger.error(f"Error loading state: {e}")
                return {"local_processed_folders": [], "last_check": None}
        return {"local_processed_folders": [], "last_check": None}
    
    def save_state(self, state: Dict):
        """Save tracker state to file"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def list_folders(self) -> List[str]:
        """
        List all folders in local data directory
        
        Returns:
            List of folder names
        """
        if not self.data_path.exists():
            return []
        
        folders = []
        for item in self.data_path.iterdir():
            if item.is_dir():
                folders.append(item.name)
        
        return sorted(folders)
    
    def get_pending_folders(self) -> List[Dict[str, str]]:
        """
        Get list of folders with their status (new/processed)
        
        Returns:
            List of dicts with 'name' and 'status'
        """
        state = self.load_state()
        processed_folders: Set[str] = set(state.get("local_processed_folders", []))
        
        all_folders = self.list_folders()
        result = []
        
        for folder_name in all_folders:
            status = "processed" if folder_name in processed_folders else "new"
            result.append({
                "name": folder_name,
                "status": status
            })
        
        return result
    
    def mark_as_processed(self, folder_name: str):
        """Mark folder as processed"""
        state = self.load_state()
        processed_folders: Set[str] = set(state.get("local_processed_folders", []))
        processed_folders.add(folder_name)
        state["local_processed_folders"] = list(processed_folders)
        state["last_check"] = datetime.now().isoformat()
        self.save_state(state)
