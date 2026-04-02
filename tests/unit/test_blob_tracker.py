"""
Unit tests for Blob Tracker
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.services.blob_tracker import BlobTracker


class TestBlobTracker:
    """Test Blob Tracker"""
    
    def test_load_state_existing(self, temp_dir):
        """Test loading existing state"""
        state_file = Path(temp_dir) / "state.json"
        state_data = {
            "processed_folders": ["folder1", "folder2"],
            "last_check": "2026-01-01T00:00:00"
        }
        
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f)
        
        tracker = BlobTracker()
        tracker.state_file = str(state_file)
        state = tracker.load_state()
        
        assert state["processed_folders"] == ["folder1", "folder2"]
        assert state["last_check"] == "2026-01-01T00:00:00"
    
    def test_load_state_not_existing(self, temp_dir):
        """Test loading non-existing state"""
        state_file = Path(temp_dir) / "nonexistent.json"
        
        tracker = BlobTracker()
        tracker.state_file = str(state_file)
        state = tracker.load_state()
        
        assert state["processed_folders"] == []
        assert state["last_check"] is None
    
    def test_save_state(self, temp_dir):
        """Test saving state"""
        state_file = Path(temp_dir) / "state.json"
        
        tracker = BlobTracker()
        tracker.state_file = str(state_file)
        
        state = {
            "processed_folders": ["folder1"],
            "last_check": "2026-01-01T00:00:00"
        }
        tracker.save_state(state)
        
        assert state_file.exists()
        
        with open(state_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        
        assert loaded["processed_folders"] == ["folder1"]
    
    @patch('app.services.blob_tracker.BlobServiceClient')
    def test_list_folders_in_blob(self, mock_blob_client_class, temp_dir):
        """Test listing folders from blob storage"""
        # Mock blob client
        mock_blob_service = Mock()
        mock_container = Mock()
        mock_blob_client_class.from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container
        
        # Mock blob list
        mock_blob1 = Mock()
        mock_blob1.name = "folder1/image1.png"
        mock_blob2 = Mock()
        mock_blob2.name = "folder1/image2.png"
        mock_blob3 = Mock()
        mock_blob3.name = "folder2/image1.png"
        mock_container.list_blobs.return_value = [mock_blob1, mock_blob2, mock_blob3]
        
        tracker = BlobTracker()
        tracker.blob_service_client = mock_blob_service
        tracker.container_client = mock_container
        
        folders = tracker.list_folders_in_blob()
        
        assert len(folders) == 2
        assert "folder1" in folders
        assert "folder2" in folders
    
    def test_list_folders_no_client(self):
        """Test listing folders without blob client"""
        tracker = BlobTracker()
        tracker.blob_service_client = None
        tracker.container_client = None
        
        folders = tracker.list_folders_in_blob()
        
        assert folders == []
    
    @patch('app.services.blob_tracker.BlobServiceClient')
    def test_check_and_process_new_folders(self, mock_blob_client_class, temp_dir):
        """Test checking and processing new folders"""
        # Mock blob client
        mock_blob_service = Mock()
        mock_container = Mock()
        mock_blob_client_class.from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container
        
        # Mock blob list
        mock_blob = Mock()
        mock_blob.name = "folder1/image1.png"
        mock_container.list_blobs.return_value = [mock_blob]
        
        # Mock download
        mock_blob_client = Mock()
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b'image data'
        mock_blob_client.download_blob.return_value = mock_download_stream
        mock_container.get_blob_client.return_value = mock_blob_client
        
        tracker = BlobTracker()
        tracker.blob_service_client = mock_blob_service
        tracker.container_client = mock_container
        tracker.state_file = str(Path(temp_dir) / "state.json")
        tracker.download_path = Path(temp_dir) / "downloads"
        
        # Mock workflow service
        with patch.object(tracker, 'workflow_service') as mock_workflow:
            mock_workflow.process_folder.return_value = {
                "success": True,
                "images_processed": 1
            }
            
            result = tracker.check_and_process_new_folders()
            
            assert result["checked"] == 1
            assert result["new"] == 1
