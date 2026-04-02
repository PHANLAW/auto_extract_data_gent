"""
Azure Blob Storage Uploader: Upload folders to blob storage
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict
from azure.storage.blob import BlobServiceClient
from app.core.config import get_settings
from app.core.logging_config import logger
from app.utils.folder_parser import get_safe_folder_name

settings = get_settings()


class BlobUploader:
    """Upload folders to Azure Blob Storage"""
    
    def __init__(self):
        """Initialize blob uploader"""
        self.container_name = settings.AZURE_BLOB_CONTAINER_NAME
        self.blob_prefix = settings.AZURE_BLOB_PREFIX
        
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
    
    def upload_folder(self, folder_path: str, folder_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Upload a folder to blob storage
        
        Args:
            folder_path: Local path to the folder
            folder_name: Optional folder name in blob storage (defaults to folder basename)
        
        Returns:
            Tuple of (success, error_message)
        """
        if not self.container_client:
            return False, "Blob container client not initialized"
        
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return False, f"Folder does not exist: {folder_path}"
        
        # Use provided folder_name or extract from path
        if not folder_name:
            folder_name = folder.name
        
        # Use safe folder name for blob storage (Windows compatibility)
        safe_folder_name = get_safe_folder_name(folder_name)
        
        try:
            uploaded_count = 0
            image_extensions = set(settings.IMAGE_EXTENSIONS.split(","))
            
            # Find all image files in folder
            image_files = []
            for ext in image_extensions:
                ext_clean = ext.strip()
                image_files.extend(folder.glob(f"*{ext_clean}"))
                image_files.extend(folder.glob(f"*{ext_clean.upper()}"))
            
            # Remove duplicates (case-insensitive filesystem)
            seen_files = set()
            unique_files = []
            for img_file in image_files:
                img_path_str = str(img_file.resolve())
                if img_path_str not in seen_files:
                    seen_files.add(img_path_str)
                    unique_files.append(img_file)
            
            if not unique_files:
                return False, "No image files found in folder"
            
            # Upload each file
            for image_file in unique_files:
                # Get relative path from folder
                relative_path = image_file.name
                
                # Construct blob name
                if self.blob_prefix:
                    blob_name = f"{self.blob_prefix}/{safe_folder_name}/{relative_path}"
                else:
                    blob_name = f"{safe_folder_name}/{relative_path}"
                
                # Upload file
                blob_client = self.container_client.get_blob_client(blob_name)
                with open(image_file, "rb") as f:
                    blob_client.upload_blob(f, overwrite=True)
                
                uploaded_count += 1
                logger.info(f"Uploaded: {blob_name}")
            
            logger.info(f"Successfully uploaded {uploaded_count} files from folder: {folder_name}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error uploading folder {folder_name}: {e}")
            return False, f"Error uploading folder: {str(e)}"
    
    def list_uploaded_folders(self) -> List[str]:
        """
        List all folders in blob storage
        
        Returns:
            List of folder names
        """
        if not self.container_client:
            logger.error("Blob container client not initialized")
            return []
        
        try:
            folders = set()
            blobs = self.container_client.list_blobs(name_starts_with=self.blob_prefix)
            
            for blob in blobs:
                # Extract folder name from blob path
                # Format: prefix/folder_name/image.png -> folder_name
                parts = blob.name.split("/")
                if len(parts) > (2 if self.blob_prefix else 1):
                    if self.blob_prefix:
                        folder_name = parts[1]  # Skip prefix
                    else:
                        folder_name = parts[0]
                    folders.add(folder_name)
            
            return sorted(list(folders))
        except Exception as e:
            logger.error(f"Error listing folders: {e}")
            return []
    
    def list_folders_with_details(self) -> List[Dict[str, Any]]:
        """
        List all folders with file counts
        
        Returns:
            List of dicts with 'name' and 'files' count
        """
        if not self.container_client:
            return []
        
        try:
            folders_dict = {}
            blobs = self.container_client.list_blobs(name_starts_with=self.blob_prefix)
            
            for blob in blobs:
                parts = blob.name.split("/")
                if len(parts) > (2 if self.blob_prefix else 1):
                    if self.blob_prefix:
                        folder_name = parts[1]
                    else:
                        folder_name = parts[0]
                    
                    if folder_name not in folders_dict:
                        folders_dict[folder_name] = 0
                    folders_dict[folder_name] += 1
            
            result = [{"name": name, "files": count} for name, count in sorted(folders_dict.items())]
            return result
        except Exception as e:
            logger.error(f"Error listing folders with details: {e}")
            return []
    
    def delete_folder(self, folder_name: str) -> Tuple[bool, Optional[str], int]:
        """
        Delete a folder and all its files from blob storage
        
        Args:
            folder_name: Name of the folder to delete
        
        Returns:
            Tuple of (success, error_message, deleted_files_count)
        """
        if not self.container_client:
            return False, "Blob container client not initialized", 0
        
        try:
            # Construct prefix
            if self.blob_prefix:
                prefix = f"{self.blob_prefix}/{folder_name}/"
            else:
                prefix = f"{folder_name}/"
            
            # List all blobs in this folder
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            
            deleted_count = 0
            for blob in blobs:
                blob_client = self.container_client.get_blob_client(blob.name)
                blob_client.delete_blob()
                deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} files from folder: {folder_name}")
            return True, None, deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting folder {folder_name}: {e}")
            return False, f"Error deleting folder: {str(e)}", 0
    
    def delete_file(self, folder_name: str, file_name: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a specific file from blob storage
        
        Args:
            folder_name: Name of the folder
            file_name: Name of the file to delete
        
        Returns:
            Tuple of (success, error_message)
        """
        if not self.container_client:
            return False, "Blob container client not initialized"
        
        try:
            # Construct blob name
            if self.blob_prefix:
                blob_name = f"{self.blob_prefix}/{folder_name}/{file_name}"
            else:
                blob_name = f"{folder_name}/{file_name}"
            
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            
            logger.info(f"Deleted file: {blob_name}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error deleting file {file_name} from folder {folder_name}: {e}")
            return False, f"Error deleting file: {str(e)}"
