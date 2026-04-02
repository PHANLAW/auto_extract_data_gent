"""
Error Handler: Write failed URLs to retry file (JSON or CSV)
"""

import json
import csv
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()


class ErrorHandler:
    """Handle errors by writing to retry files"""
    
    def __init__(self, retry_file: Optional[str] = None, file_format: Optional[str] = None, warning_matches_file: Optional[str] = None):
        """
        Initialize Error Handler
        
        Args:
            retry_file: Path to retry file (defaults to config)
            file_format: Format of retry file "json" or "csv" (defaults to config)
            warning_matches_file: Path to warning matches file (defaults to config)
        """
        self.retry_file = retry_file or settings.RETRY_FILE
        self.file_format = (file_format or settings.RETRY_FILE_FORMAT).lower()
        self.warning_matches_file = warning_matches_file or settings.WARNING_MATCHES_FILE
        self.ensure_file_exists()
        self.ensure_warning_file_exists()
    
    def ensure_file_exists(self):
        """Ensure retry file exists, create if not"""
        if not os.path.exists(self.retry_file):
            if self.file_format == "json":
                with open(self.retry_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            else:  # CSV
                with open(self.retry_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["error_type", "match_name", "image_name", "url", "folder_name", "error", "timestamp"])
    
    def ensure_warning_file_exists(self):
        """Ensure warning matches file exists, create if not"""
        if not os.path.exists(self.warning_matches_file):
            # Ensure directory exists
            warning_dir = os.path.dirname(self.warning_matches_file)
            if warning_dir and not os.path.exists(warning_dir):
                os.makedirs(warning_dir, exist_ok=True)
            
            # Create file with empty array
            with open(self.warning_matches_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def write_failed_url(self, match_name: str, image_name: str, url: str, error: str = "", error_type: str = "detect_error"):
        """
        Write failed URL to retry file (when detected_link_id not found)
        
        Args:
            match_name: Name of the match
            image_name: Name of the image file
            url: URL that failed
            error: Error message (optional)
            error_type: Type of error (default: "detect_error")
        """
        entry = {
            "error_type": error_type,
            "match_name": match_name,
            "image_name": image_name,
            "url": url,
            "folder_name": None,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self._write_entry(entry)
        logger.info(f"Written failed URL to retry file: {match_name}/{image_name}")
    
    def write_failed_extraction(self, match_name: str, image_name: str, error: str = "", error_type: str = "extract_error"):
        """
        Write failed URL extraction to retry file (when URL cannot be extracted from image)
        
        Args:
            match_name: Name of the match
            image_name: Name of the image file
            error: Error message
            error_type: Type of error (default: "extract_error", can be "not_web_image" for non-web screenshots)
        """
        entry = {
            "error_type": error_type,
            "match_name": match_name,
            "image_name": image_name,
            "url": None,
            "folder_name": None,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self._write_entry(entry)
        logger.info(f"Written failed extraction to retry file: {match_name}/{image_name}")
    
    def write_failed_sport_id(self, folder_name: str, match_name: str, league: str, start_time: str, error: str = ""):
        """
        Write failed sport_id lookup to retry file (when sport_id cannot be found)
        
        Args:
            folder_name: Name of the folder
            match_name: Name of the match
            league: League name
            start_time: Start time
            error: Error message
        """
        entry = {
            "error_type": "sport_id_error",
            "match_name": match_name,
            "image_name": None,
            "url": None,
            "folder_name": folder_name,
            "error": f"Cannot get sport_id for match={match_name}, league={league}, start_time={start_time}. {error}",
            "timestamp": datetime.now().isoformat()
        }
        self._write_entry(entry)
        logger.info(f"Written failed sport_id lookup to retry file: {folder_name}")
    
    def write_warning_match(
        self,
        match_name: str,
        image_name: str,
        url: str,
        error: str,
        error_type: str
    ):
        """
        Write AI-guessed match to warning matches file (when similarity/agent matched)
        
        Args:
            match_name: Name of the match
            image_name: Name of the image file
            url: OCR'd URL that was matched
            error: Match details (e.g., "detect_guess_similarity: matched <id> from <url> with similarity=0.95")
            error_type: Type of guess ("detect_guess_similarity" or "detect_guess_by_agent")
        """
        entry = {
            "error_type": error_type,
            "match_name": match_name,
            "image_name": image_name,
            "url": url,
            "folder_name": None,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self._write_warning_entry(entry)
        logger.info(f"Written warning match to {self.warning_matches_file}: {match_name}/{image_name}")
    
    def _write_warning_entry(self, entry: Dict):
        """Internal method to write entry to warning matches file"""
        # Ensure file exists before writing
        self.ensure_warning_file_exists()
        
        # Always use JSON format for warning matches file
        try:
            if os.path.exists(self.warning_matches_file):
                with open(self.warning_matches_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            else:
                entries = []
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading warning matches file, starting fresh: {e}")
            entries = []
        
        # Add new entry
        entries.append(entry)
        
        # Write back
        try:
            with open(self.warning_matches_file, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Error writing to warning matches file: {e}")
            raise
    
    def _write_entry(self, entry: Dict):
        """Internal method to write entry to retry file"""
        if self.file_format == "json":
            # Read existing entries
            if os.path.exists(self.retry_file):
                try:
                    with open(self.retry_file, "r", encoding="utf-8") as f:
                        entries = json.load(f)
                except:
                    entries = []
            else:
                entries = []
            
            # Add new entry
            entries.append(entry)
            
            # Write back
            with open(self.retry_file, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
        else:  # CSV
            with open(self.retry_file, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    entry.get("error_type", ""),
                    entry.get("match_name", ""),
                    entry.get("image_name", ""),
                    entry.get("url", ""),
                    entry.get("folder_name", ""),
                    entry.get("error", ""),
                    entry.get("timestamp", "")
                ])
    
    def read_failed_urls(self) -> List[Dict]:
        """Read all failed URLs from retry file"""
        if not os.path.exists(self.retry_file):
            return []
        
        if self.file_format == "json":
            try:
                with open(self.retry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        else:  # CSV
            entries = []
            try:
                with open(self.retry_file, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    entries = list(reader)
            except:
                pass
            return entries
