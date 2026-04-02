"""
Agent Manager: Manage and reuse agent instances (Singleton pattern)
"""

from typing import Optional
from openai import AzureOpenAI
from app.core.config import get_settings
from app.utils.sport_api import SportAPIClient
from app.tools.url_extractor_tool import URLExtractorTool
from app.tools.api_tools import DetectLinkTool, UploadImageTool
from app.utils.error_handler import ErrorHandler
from app.agents.image_processing_agent import ImageProcessingAgent
from app.core.logging_config import logger

settings = get_settings()


class AgentManager:
    """
    Singleton manager for agent instances
    Provides agent reuse and centralized management
    """
    
    _instance: Optional['AgentManager'] = None
    _agent: Optional[ImageProcessingAgent] = None
    _azure_client: Optional[AzureOpenAI] = None
    _api_client: Optional[SportAPIClient] = None
    _error_handler: Optional[ErrorHandler] = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize agent manager (only once)"""
        if self._agent is None:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all components"""
        try:
            # Initialize Azure OpenAI client with retry configuration
            # The client uses httpx internally and has built-in retry for 429 errors
            # We also add delay between requests in workflow_service to prevent rate limiting
            self._azure_client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                max_retries=3,  # Maximum number of retries for failed requests
                timeout=60.0  # 60 second timeout per request
            )
            
            # Initialize Sport API client
            self._api_client = SportAPIClient(
                base_url=settings.SPORT_API_BASE_URL,
                username=settings.SPORT_API_USERNAME,
                password=settings.SPORT_API_PASSWORD
            )
            
            # Initialize error handler
            self._error_handler = ErrorHandler(
                retry_file=settings.RETRY_FILE,
                file_format=settings.RETRY_FILE_FORMAT
            )
            
            # Initialize tools
            url_extractor_tool = URLExtractorTool(self._azure_client)
            detect_link_tool = DetectLinkTool(self._api_client)
            upload_image_tool = UploadImageTool(self._api_client)
            
            # Initialize agent
            self._agent = ImageProcessingAgent(
                url_extractor_tool=url_extractor_tool,
                detect_link_tool=detect_link_tool,
                upload_image_tool=upload_image_tool,
                error_handler=self._error_handler
            )
            
            logger.info("AgentManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing AgentManager: {e}")
            raise
    
    def get_agent(self) -> ImageProcessingAgent:
        """
        Get agent instance (reused)
        
        Returns:
            ImageProcessingAgent instance
        """
        if self._agent is None:
            self._initialize_components()
        return self._agent
    
    def get_azure_client(self) -> AzureOpenAI:
        """Get Azure OpenAI client"""
        if self._azure_client is None:
            self._initialize_components()
        return self._azure_client
    
    def get_api_client(self) -> SportAPIClient:
        """Get Sport API client"""
        if self._api_client is None:
            self._initialize_components()
        return self._api_client
    
    def get_error_handler(self) -> ErrorHandler:
        """Get error handler"""
        if self._error_handler is None:
            self._initialize_components()
        return self._error_handler
    
    def reset(self):
        """Reset all components (for testing)"""
        self._agent = None
        self._azure_client = None
        self._api_client = None
        self._error_handler = None
        logger.info("AgentManager reset")


# Global singleton instance
agent_manager = AgentManager()
