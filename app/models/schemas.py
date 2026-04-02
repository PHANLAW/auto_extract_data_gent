"""
Pydantic Schemas for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Current timestamp")


# Processing API Schemas
class BlobAutoRequest(BaseModel):
    """Request to enable/disable blob auto-processing"""
    enabled: bool = Field(..., description="Enable or disable auto-processing")


class BlobAutoResponse(BaseModel):
    """Response for blob auto-processing toggle"""
    success: bool = Field(..., description="Whether operation was successful")
    enabled: bool = Field(..., description="Current enabled state")
    error: Optional[str] = Field(None, description="Error message if failed")


class PendingFolderInfo(BaseModel):
    """Information about a pending folder"""
    name: str = Field(..., description="Folder name")
    status: str = Field(..., description="Status: 'new' or 'processed'")


class PendingFoldersResponse(BaseModel):
    """Response for pending folders check"""
    mode: str = Field(..., description="Data source mode: 'local' or 'blob_storage'")
    source: str = Field(..., description="Source path or container name")
    folders: List[PendingFolderInfo] = Field(..., description="List of folders with status")


class ProcessingStartRequest(BaseModel):
    """Request to start processing"""
    mode: str = Field(default="auto", description="Processing mode: 'auto', 'local', or 'blob_storage'")
    max_folders: Optional[int] = Field(None, description="Maximum number of folders to process")


class ProcessingStartResponse(BaseModel):
    """Response for processing start"""
    success: bool = Field(..., description="Whether processing started successfully")
    mode: str = Field(..., description="Processing mode used")
    checked: int = Field(..., description="Number of folders checked")
    new_folders: int = Field(..., description="Number of new folders found")
    processed: int = Field(..., description="Number of folders processed")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Processing results for each folder")
    error: Optional[str] = Field(None, description="Error message if failed")


# Blob Storage API Schemas
class BlobUploadFolderRequest(BaseModel):
    """Request to upload folder to blob storage"""
    local_folder_path: str = Field(..., description="Local path to folder")
    target_folder_name: Optional[str] = Field(None, description="Target folder name in blob storage (optional)")


class BlobUploadFolderResponse(BaseModel):
    """Response for folder upload"""
    success: bool = Field(..., description="Whether upload was successful")
    folder_name: str = Field(..., description="Folder name in blob storage")
    uploaded_files: int = Field(..., description="Number of files uploaded")
    error: Optional[str] = Field(None, description="Error message if failed")


class BlobFolderInfo(BaseModel):
    """Information about a blob folder"""
    name: str = Field(..., description="Folder name")
    files: int = Field(..., description="Number of files in folder")


class BlobListFoldersResponse(BaseModel):
    """Response for listing blob folders"""
    folders: List[BlobFolderInfo] = Field(..., description="List of folders")
    total: int = Field(..., description="Total number of folders")


class BlobDeleteFolderResponse(BaseModel):
    """Response for deleting blob folder"""
    success: bool = Field(..., description="Whether deletion was successful")
    deleted_files: int = Field(..., description="Number of files deleted")
    error: Optional[str] = Field(None, description="Error message if failed")


class BlobDeleteFileRequest(BaseModel):
    """Request to delete a file from blob storage"""
    folder_name: str = Field(..., description="Folder name")
    file_name: str = Field(..., description="File name to delete")


class BlobDeleteFileResponse(BaseModel):
    """Response for deleting blob file"""
    success: bool = Field(..., description="Whether deletion was successful")
    error: Optional[str] = Field(None, description="Error message if failed")
