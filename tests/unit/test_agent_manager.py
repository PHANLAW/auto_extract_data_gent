"""
Unit tests for Agent Manager
"""

import pytest
from unittest.mock import patch, Mock
from app.core.agent_manager import AgentManager


class TestAgentManager:
    """Test Agent Manager singleton"""
    
    def test_singleton_pattern(self, reset_agent_manager):
        """Test that AgentManager is a singleton"""
        manager1 = AgentManager()
        manager2 = AgentManager()
        
        assert manager1 is manager2
        assert manager1._instance is manager2._instance
    
    @patch('app.core.agent_manager.AzureOpenAI')
    @patch('app.core.agent_manager.SportAPIClient')
    @patch('app.core.agent_manager.ErrorHandler')
    @patch('app.core.agent_manager.URLExtractorTool')
    @patch('app.core.agent_manager.DetectLinkTool')
    @patch('app.core.agent_manager.UploadImageTool')
    @patch('app.core.agent_manager.ImageProcessingAgent')
    def test_get_agent(self, mock_agent_class, mock_upload, mock_detect, 
                      mock_extract, mock_error, mock_api, mock_azure, reset_agent_manager):
        """Test getting agent instance"""
        manager = AgentManager()
        
        # Mock initialization
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        # Reset to force re-initialization
        manager.reset()
        
        # Get agent (will initialize)
        agent = manager.get_agent()
        
        # Should return the same instance on subsequent calls
        agent2 = manager.get_agent()
        assert agent is agent2
    
    def test_reset(self, reset_agent_manager):
        """Test resetting manager"""
        manager = AgentManager()
        manager.reset()
        
        assert manager._agent is None
        assert manager._azure_client is None
        assert manager._api_client is None
