"""
API Dependencies: Dependency injection for FastAPI
"""

from app.core.agent_manager import agent_manager
from app.services.workflow_service import WorkflowService
from app.services.blob_tracker import BlobTracker
from app.services.blob_uploader import BlobUploader
from app.services.local_folder_tracker import LocalFolderTracker
from app.services.processing_manager import ProcessingManager
from app.agents.image_processing_agent import ImageProcessingAgent
from app.utils.sport_api import SportAPIClient
from app.utils.error_handler import ErrorHandler


def get_image_processing_agent() -> ImageProcessingAgent:
    """Get image processing agent (reused via AgentManager)"""
    return agent_manager.get_agent()


def get_sport_api_client() -> SportAPIClient:
    """Get Sport API client (reused via AgentManager)"""
    return agent_manager.get_api_client()


def get_error_handler() -> ErrorHandler:
    """Get error handler (reused via AgentManager)"""
    return agent_manager.get_error_handler()


def get_workflow_service() -> WorkflowService:
    """Get workflow service"""
    return WorkflowService()


def get_blob_tracker() -> BlobTracker:
    """Get blob tracker"""
    return BlobTracker()


def get_blob_uploader() -> BlobUploader:
    """Get blob uploader"""
    return BlobUploader()


def get_local_folder_tracker() -> LocalFolderTracker:
    """Get local folder tracker"""
    return LocalFolderTracker()


def get_processing_manager() -> ProcessingManager:
    """Get processing manager"""
    return ProcessingManager()
