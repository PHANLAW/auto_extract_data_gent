"""
Sample data fixtures for testing
"""

import os
import sys
from pathlib import Path
from app.utils.folder_parser import get_safe_folder_name


def create_sample_folder_structure(base_path: str) -> dict:
    """
    Create sample folder structure for testing
    
    Returns:
        Dictionary with folder paths
    """
    base = Path(base_path)
    
    # Original folder name (with colon)
    original_folder_name = "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
    # Use safe folder name for Windows compatibility
    folder_name = get_safe_folder_name(original_folder_name) if sys.platform == "win32" else original_folder_name
    folder_path = base / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Create sample images
    image1 = folder_path / "image1.png"
    image1.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
    
    image2 = folder_path / "image2.jpg"
    image2.write_bytes(b'\xff\xd8\xff\xe0' + b'0' * 100)
    
    return {
        "base_path": str(base),
        "folder_name": folder_name,
        "original_folder_name": original_folder_name,  # Keep original for parsing tests
        "folder_path": str(folder_path),
        "images": [str(image1), str(image2)]
    }


def create_multiple_folders(base_path: str) -> list:
    """Create multiple sample folders"""
    original_folders = [
        "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham",
        "15.12.25 14:30 EPL 24_25 Manchester United - Liverpool",
        "01.06.26 20:00 La Liga 25_26 Barcelona - Real Madrid"
    ]
    
    created = []
    base = Path(base_path)
    
    for original_folder_name in original_folders:
        # Use safe folder name for Windows compatibility
        folder_name = get_safe_folder_name(original_folder_name) if sys.platform == "win32" else original_folder_name
        folder_path = base / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Create at least one image
        image = folder_path / "test.png"
        image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        
        created.append({
            "name": folder_name,
            "original_name": original_folder_name,  # Keep original for parsing tests
            "path": str(folder_path)
        })
    
    return created
