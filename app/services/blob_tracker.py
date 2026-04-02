"""
Azure Blob Storage Tracker: Track and process new folders from blob storage
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContainerClient
from app.core.config import get_settings
from app.core.logging_config import logger
from app.services.workflow_service import WorkflowService
from app.utils.folder_parser import get_safe_folder_name

settings = get_settings()


class BlobTracker:
    """Track and process folders from Azure Blob Storage"""
    
    def __init__(self):
        """Initialize blob tracker"""
        self.workflow_service = WorkflowService()
        self.state_file = settings.TRACKER_STATE_FILE
        self.container_name = settings.AZURE_BLOB_CONTAINER_NAME
        self.blob_prefix = settings.AZURE_BLOB_PREFIX
        self.download_path = Path(settings.AZURE_BLOB_DOWNLOAD_PATH)
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize blob service client
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
        else:
            self.blob_service_client = None
            self.container_client = None
            logger.warning("Azure Storage Connection String not configured")
    
    def load_state(self) -> Dict:
        """Load tracker state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading state: {e}")
                return {"processed_folders": [], "last_check": None}
        return {"processed_folders": [], "last_check": None}
    
    def save_state(self, state: Dict):
        """Save tracker state to file"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def list_folders_in_blob(self) -> List[str]:
        """
        List all folder prefixes in blob storage
        
        Returns:
            List of folder names (prefixes)
        """
        if not self.container_client:
            logger.error("Blob container client not initialized")
            return []
        
        try:
            folders = set()
            blobs = self.container_client.list_blobs(name_starts_with=self.blob_prefix)
            
            for blob in blobs:
                # Extract folder name from blob path
                # Format: folder_name/image.png -> folder_name
                parts = blob.name.split("/")
                if len(parts) > 1:
                    folder_name = parts[0]
                    folders.add(folder_name)
            
            return sorted(list(folders))
        except Exception as e:
            logger.error(f"Error listing folders from blob: {e}")
            return []
    
    def download_folder_from_blob(self, folder_name: str) -> Optional[str]:
        """
        Download a folder from blob storage to local temp directory
        
        Args:
            folder_name: Name of the folder in blob storage
        
        Returns:
            Local path to downloaded folder or None if error
        """
        if not self.container_client:
            return None
        
        try:
            # Sanitize folder name for Windows (replace : with - in time part only)
            safe_folder_name = get_safe_folder_name(folder_name)
            local_folder = self.download_path / safe_folder_name
            local_folder.mkdir(parents=True, exist_ok=True)
            
            # List all blobs in this folder
            prefix = f"{folder_name}/" if not self.blob_prefix else f"{self.blob_prefix}/{folder_name}/"
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            
            downloaded_count = 0
            for blob in blobs:
                # Get relative path within folder
                relative_path = blob.name.replace(prefix, "")
                if not relative_path:  # Skip if it's the folder itself
                    continue
                
                local_file = local_folder / relative_path
                local_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Download blob
                blob_client = self.container_client.get_blob_client(blob.name)
                with open(local_file, "wb") as f:
                    download_stream = blob_client.download_blob()
                    f.write(download_stream.readall())
                
                downloaded_count += 1
            
            logger.info(f"Downloaded {downloaded_count} files from folder: {folder_name}")
            return str(local_folder)
            
        except Exception as e:
            logger.error(f"Error downloading folder {folder_name}: {e}")
            return None
    
    def cleanup_downloaded_folder(self, folder_path: str):
        """Cleanup downloaded folder after processing"""
        try:
            import shutil
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                logger.info(f"Cleaned up folder: {folder_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up folder {folder_path}: {e}")
    
    def check_and_process_new_folders(self) -> Dict:
        """
        Check for new folders and process them
        
        Returns:
            Dictionary with processing results
        """
        state = self.load_state()
        processed_folders: Set[str] = set(state.get("processed_folders", []))
        
        # List folders from blob storage
        all_folders = self.list_folders_in_blob()
        
        # Find new folders
        new_folders = [f for f in all_folders if f not in processed_folders]
        
        if not new_folders:
            logger.info("No new folders found")
            return {
                "checked": len(all_folders),
                "new": 0,
                "processed": 0,
                "results": []
            }
        
        logger.info(f"Found {len(new_folders)} new folders")
        
        results = []
        for folder_name in new_folders:
            try:
                # Download folder
                local_folder = self.download_folder_from_blob(folder_name)
                if not local_folder:
                    logger.error(f"Failed to download folder: {folder_name}")
                    continue
                
                # Process folder
                result = self.workflow_service.process_folder(local_folder)
                results.append(result)
                
                # Mark as processed
                processed_folders.add(folder_name)
                
                # Cleanup
                self.cleanup_downloaded_folder(local_folder)
                
            except Exception as e:
                logger.error(f"Error processing folder {folder_name}: {e}")
                results.append({
                    "folder": folder_name,
                    "success": False,
                    "error": str(e)
                })
        
        # Update state
        state["processed_folders"] = list(processed_folders)
        state["last_check"] = datetime.now().isoformat()
        self.save_state(state)
        
        return {
            "checked": len(all_folders),
            "new": len(new_folders),
            "processed": len([r for r in results if r.get("success")]),
            "results": results
        }
    
    async def start_auto_processing(self):
        """Start automatic processing loop"""
        if not settings.AUTO_PROCESS_ENABLED:
            logger.info("Auto processing is disabled")
            return
        
        logger.info(f"Starting auto processing (interval: {settings.AUTO_PROCESS_INTERVAL}s)")
        
        while True:
            try:
                result = self.check_and_process_new_folders()
                logger.info(
                    f"Auto check completed - Checked: {result['checked']}, "
                    f"New: {result['new']}, Processed: {result['processed']}"
                )
            except Exception as e:
                logger.error(f"Error in auto processing: {e}")
            
            await asyncio.sleep(settings.AUTO_PROCESS_INTERVAL)
