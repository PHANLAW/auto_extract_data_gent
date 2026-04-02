"""
API Routes: FastAPI endpoints - Orchestrator and Auto Handler APIs only
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pathlib import Path
from typing import List, Dict, Any
import os

from app.models.schemas import (
    HealthResponse,
    BlobAutoRequest, BlobAutoResponse,
    PendingFoldersResponse, PendingFolderInfo,
    ProcessingStartRequest, ProcessingStartResponse,
    BlobUploadFolderRequest, BlobUploadFolderResponse,
    BlobListFoldersResponse, BlobFolderInfo,
    BlobDeleteFolderResponse,
    BlobDeleteFileRequest, BlobDeleteFileResponse
)
from app.api.dependencies import (
    get_workflow_service,
    get_blob_tracker,
    get_blob_uploader,
    get_local_folder_tracker,
    get_processing_manager
)
from app.core.logging_config import logger
from app.core.config import get_settings
from datetime import datetime

settings = get_settings()

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now()
    )


# ============================================================================
# PROCESSING APIs - Workflow Control
# ============================================================================

@router.post("/processing/blob-auto", response_model=BlobAutoResponse)
async def set_blob_auto(
    request: BlobAutoRequest,
    processing_manager = Depends(get_processing_manager)
):
    """
    Enable/disable blob auto-processing
    
    Only valid when DATA_SOURCE_MODE=blob_storage
    """
    if settings.DATA_SOURCE_MODE != "blob_storage":
        return BlobAutoResponse(
            success=False,
            enabled=False,
            error="Only valid when DATA_SOURCE_MODE=blob_storage"
        )
    
    success = processing_manager.set_blob_auto_enabled(request.enabled)
    if not success:
        return BlobAutoResponse(
            success=False,
            enabled=False,
            error="Failed to set blob auto-processing state"
        )
    
    return BlobAutoResponse(
        success=True,
        enabled=request.enabled
    )


@router.get("/processing/pending-folders", response_model=PendingFoldersResponse)
async def get_pending_folders(
    local_tracker = Depends(get_local_folder_tracker),
    blob_tracker = Depends(get_blob_tracker)
):
    """
    Check for folders that need processing
    
    Returns different results based on DATA_SOURCE_MODE:
    - local: Lists folders in LOCAL_DATA_PATH with status
    - blob_storage: Lists folders in blob storage with status
    """
    if settings.DATA_SOURCE_MODE == "local":
        folders_info = local_tracker.get_pending_folders()
        folders = [PendingFolderInfo(**f) for f in folders_info]
        
        return PendingFoldersResponse(
            mode="local",
            source=settings.LOCAL_DATA_PATH,
            folders=folders
        )
    
    elif settings.DATA_SOURCE_MODE == "blob_storage":
        # Get folders from blob
        all_folders = blob_tracker.list_folders_in_blob()
        state = blob_tracker.load_state()
        processed_folders = set(state.get("processed_folders", []))
        
        folders = []
        for folder_name in all_folders:
            status = "processed" if folder_name in processed_folders else "new"
            folders.append(PendingFolderInfo(name=folder_name, status=status))
        
        return PendingFoldersResponse(
            mode="blob_storage",
            source=settings.AZURE_BLOB_CONTAINER_NAME,
            folders=folders
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid DATA_SOURCE_MODE: {settings.DATA_SOURCE_MODE}"
        )


@router.post("/processing/start", response_model=ProcessingStartResponse)
async def start_processing(
    request: ProcessingStartRequest,
    workflow_service = Depends(get_workflow_service),
    local_tracker = Depends(get_local_folder_tracker),
    blob_tracker = Depends(get_blob_tracker)
):
    """
    Start processing folders
    
    Workflow:
    - If mode='auto': Uses DATA_SOURCE_MODE from config
    - If mode='local': Processes folders from LOCAL_DATA_PATH
    - If mode='blob_storage': Processes folders from blob storage
    
    For each folder:
    1. Parse folder name
    2. Get league_id and sport_id (calls external Sport API)
    3. Process all images:
       - Extract URL from image
       - Check detected_link exists
       - Upload image if detected_link exists
    """
    # Determine actual mode
    if request.mode == "auto":
        actual_mode = settings.DATA_SOURCE_MODE
    else:
        actual_mode = request.mode
    
    if actual_mode not in ["local", "blob_storage"]:
        return ProcessingStartResponse(
            success=False,
            mode=actual_mode,
            checked=0,
            new_folders=0,
            processed=0,
            error=f"Invalid mode: {actual_mode}"
        )
    
    try:
        if actual_mode == "local":
            # Process local folders
            folders_info = local_tracker.get_pending_folders()
            new_folders = [f["name"] for f in folders_info if f["status"] == "new"]
            
            if not new_folders:
                return ProcessingStartResponse(
                    success=True,
                    mode="local",
                    checked=len(folders_info),
                    new_folders=0,
                    processed=0,
                    results=[]
                )
            
            # Limit by max_folders if specified
            if request.max_folders:
                new_folders = new_folders[:request.max_folders]
            
            results = []
            for folder_name in new_folders:
                folder_path = os.path.join(settings.LOCAL_DATA_PATH, folder_name)
                result = workflow_service.process_folder(folder_path)
                results.append(result)
                
                # Mark as processed if successful
                if result.get("success"):
                    local_tracker.mark_as_processed(folder_name)
            
            processed_count = sum(1 for r in results if r.get("success"))
            
            return ProcessingStartResponse(
                success=True,
                mode="local",
                checked=len(folders_info),
                new_folders=len(new_folders),
                processed=processed_count,
                results=results
            )
        
        else:  # blob_storage
            # Process blob folders
            result = blob_tracker.check_and_process_new_folders()
            
            return ProcessingStartResponse(
                success=True,
                mode="blob_storage",
                checked=result["checked"],
                new_folders=result["new"],
                processed=result["processed"],
                results=result["results"]
            )
    
    except Exception as e:
        logger.error(f"Error starting processing: {e}")
        return ProcessingStartResponse(
            success=False,
            mode=actual_mode,
            checked=0,
            new_folders=0,
            processed=0,
            error=str(e)
        )


# ============================================================================
# BLOB STORAGE APIs - Blob Management
# ============================================================================

@router.post("/blob/folders/upload", response_model=BlobUploadFolderResponse)
async def upload_folder(
    request: BlobUploadFolderRequest,
    uploader = Depends(get_blob_uploader)
):
    """
    Upload a folder to Azure Blob Storage
    
    Uploads all image files from local folder to blob storage
    """
    if not os.path.exists(request.local_folder_path):
        return BlobUploadFolderResponse(
            success=False,
            folder_name=os.path.basename(request.local_folder_path),
            uploaded_files=0,
            error=f"Folder does not exist: {request.local_folder_path}"
        )
    
    folder_name = request.target_folder_name or os.path.basename(request.local_folder_path)
    success, error = uploader.upload_folder(request.local_folder_path, folder_name)
    
    if not success:
        return BlobUploadFolderResponse(
            success=False,
            folder_name=folder_name,
            uploaded_files=0,
            error=error
        )
    
    # Count uploaded files
    folder = Path(request.local_folder_path)
    image_extensions = set(settings.IMAGE_EXTENSIONS.split(","))
    image_files = []
    for ext in image_extensions:
        ext_clean = ext.strip()
        image_files.extend(folder.glob(f"*{ext_clean}"))
        image_files.extend(folder.glob(f"*{ext_clean.upper()}"))
    
    # Remove duplicates
    seen = set()
    unique_files = []
    for img in image_files:
        img_str = str(img.resolve())
        if img_str not in seen:
            seen.add(img_str)
            unique_files.append(img)
    
    return BlobUploadFolderResponse(
        success=True,
        folder_name=folder_name,
        uploaded_files=len(unique_files)
    )


@router.get("/blob/folders", response_model=BlobListFoldersResponse)
async def list_blob_folders(
    name: str = None,
    uploader = Depends(get_blob_uploader)
):
    """
    List all folders in blob storage
    
    Query params:
    - name: Optional filter by folder name (partial match)
    """
    folders_info = uploader.list_folders_with_details()
    
    # Filter by name if provided
    if name:
        folders_info = [f for f in folders_info if name.lower() in f["name"].lower()]
    
    return BlobListFoldersResponse(
        folders=[BlobFolderInfo(**f) for f in folders_info],
        total=len(folders_info)
    )


@router.delete("/blob/folders/{folder_name}", response_model=BlobDeleteFolderResponse)
async def delete_blob_folder(
    folder_name: str,
    uploader = Depends(get_blob_uploader)
):
    """
    Delete a folder and all its files from blob storage
    """
    success, error, deleted_count = uploader.delete_folder(folder_name)
    
    return BlobDeleteFolderResponse(
        success=success,
        deleted_files=deleted_count,
        error=error
    )


@router.delete("/blob/files", response_model=BlobDeleteFileResponse)
async def delete_blob_file(
    request: BlobDeleteFileRequest,
    uploader = Depends(get_blob_uploader)
):
    """
    Delete a specific file from blob storage
    """
    success, error = uploader.delete_file(request.folder_name, request.file_name)
    
    return BlobDeleteFileResponse(
        success=success,
        error=error
    )
