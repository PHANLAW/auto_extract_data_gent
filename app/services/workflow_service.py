"""
Workflow Service: Orchestrate folder parsing, API calls, and image processing
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from app.utils.folder_parser import parse_folder_name
from app.core.agent_manager import agent_manager
from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()


class WorkflowService:
    """Service for processing folders and images"""
    
    def __init__(self):
        """Initialize workflow service"""
        self.agent = agent_manager.get_agent()
        self.api_client = agent_manager.get_api_client()
        self.error_handler = agent_manager.get_error_handler()
        self.image_extensions = set(settings.IMAGE_EXTENSIONS.split(","))
    
    def process_folder(self, folder_path: str) -> Dict:
        """
        Process a single folder:
        1. Parse folder name
        2. Get sport_id from API
        3. Process all images in folder
        
        Args:
            folder_path: Path to the folder
        
        Returns:
            Dictionary with processing results
        """
        folder_name = os.path.basename(folder_path)
        logger.info(f"Processing folder: {folder_name}")
        
        # Step 1: Parse folder name
        start_time, league, match_name, original_start_time = parse_folder_name(folder_name)
        
        if not all([start_time, league, match_name]):
            error_msg = f"Cannot parse folder name: {folder_name}"
            logger.error(error_msg)
            return {
                "folder": folder_name,
                "success": False,
                "error": error_msg,
                "images_processed": 0
            }
        
        logger.info(f"Parsed - Match: {match_name}, League: {league}, Time: {start_time}")
        
        # Step 2: Get sport_id from API
        sport_id, api_error = self.api_client.get_sport_id(
            match_name=match_name,
            start_time=start_time,
            league=league
        )
        
        if api_error or not sport_id:
            error_msg = f"Cannot get sport_id: {api_error}"
            logger.error(error_msg)
            
            # Write to retry file for later retry
            self.error_handler.write_failed_sport_id(
                folder_name=folder_name,
                match_name=match_name,
                league=league,
                start_time=start_time,
                error=api_error or "No sport_id returned"
            )
            
            return {
                "folder": folder_name,
                "success": False,
                "error": error_msg,
                "error_type": "sport_id_error",
                "images_processed": 0
            }
        
        logger.info(f"Got sport_id: {sport_id}")
        
        # Step 3: Process all images in folder
        image_files = self._find_images(folder_path)
        
        if not image_files:
            logger.warning(f"No images found in folder: {folder_name}")
            return {
                "folder": folder_name,
                "success": True,
                "match_name": match_name,
                "league": league,
                "start_time": start_time,
                "sport_id": sport_id,
                "images_processed": 0
            }
        
        logger.info(f"Found {len(image_files)} images")
        
        # Prepare results container
        results = {
            "folder": folder_name,
            "match_name": match_name,
            "league": league,
            "start_time": start_time,
            "sport_id": sport_id,
            "images_processed": 0,
            "images_success": 0,
            "images_failed": 0,
            "image_results": []
        }
        
        total_images = len(image_files)
        
        # Build indexed list so we can keep stable ordering
        indexed_images = [
            {
                "id": idx,
                "path": str(image_path)
            }
            for idx, image_path in enumerate(image_files, 1)
        ]
        
        # Process images with ONE image per agent call (user requirement)
        # Previously this was a small batch (<= 2), but now we keep it at 1
        batch_size = 1
        for batch_start in range(0, total_images, batch_size):
            batch = indexed_images[batch_start:batch_start + batch_size]
            
            # Log which images are in this batch
            for item in batch:
                image_name = os.path.basename(item["path"])
                logger.info(f"[{item['id']}/{total_images}] Queued for processing: {image_name}")
            
            # Build payload for agent batch call
            agent_batch_payload = [
                {
                    "id": item["id"],
                    "image_path": item["path"],
                    "match_name": match_name,
                    "sport_id": sport_id
                }
                for item in batch
            ]
            
            try:
                batch_results = self.agent.process_images_batch(agent_batch_payload)
            except Exception as e:
                # Check if it's a rate limit error (429)
                error_str = str(e).lower()
                if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
                    # Increase delay after 429 error
                    retry_delay = settings.AZURE_OPENAI_RETRY_DELAY
                    logger.warning(f"Rate limit (429) detected in batch processing, waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Retry the batch
                    # NOTE: 429 errors typically occur during OCR (Azure OpenAI), BEFORE upload
                    # So retry should be safe. However, if upload already succeeded, API will return 409 (Conflict)
                    # which is handled as success in sport_api.py, preventing duplicate uploads.
                    try:
                        batch_results = self.agent.process_images_batch(agent_batch_payload)
                    except Exception as retry_error:
                        # If retry also fails, check if any images were already uploaded
                        # Create error results for the batch
                        batch_results = []
                        for item in batch:
                            batch_results.append({
                                "success": False,
                                "url": None,
                                "detected_link_id": None,
                                "error": f"Retry failed after 429: {str(retry_error)}",
                                "error_type": "retry_error",
                                "image_id": item["id"]
                            })
                        logger.error(f"Retry failed after 429 error: {retry_error}")
                else:
                    # Re-raise if it's not a rate limit error
                    raise
            
            # Add delay between requests to avoid rate limiting (429 errors)
            # Only delay if not the last batch
            if batch_start + batch_size < total_images:
                delay = settings.AZURE_OPENAI_REQUEST_DELAY
                logger.debug(f"Waiting {delay} seconds before next batch...")
                time.sleep(delay)
            
            # Merge batch results back into folder-level summary, preserving order
            for item, result in zip(batch, batch_results):
                image_name = os.path.basename(item["path"])
                
                results["images_processed"] += 1
                
                if result.get("success"):
                    results["images_success"] += 1
                    logger.info(f"Success - [{item['id']}/{total_images}] {image_name} - URL: {result.get('url')}, Link ID: {result.get('detected_link_id')}")
                else:
                    results["images_failed"] += 1
                    error_type = result.get("error_type", "unknown")
                    error_msg = result.get('error', 'Unknown error')
                    # Sanitize error message for logging to avoid UnicodeEncodeError
                    from app.core.logging_config import sanitize_log_message
                    safe_error_msg = sanitize_log_message(error_msg)
                    logger.warning(f"Failed ({error_type}) - [{item['id']}/{total_images}] {image_name}: {safe_error_msg}")
                
                results["image_results"].append({
                    "index": item["id"],
                    "image": image_name,
                    "success": result.get("success", False),
                    "url": result.get("url"),
                    "detected_link_id": result.get("detected_link_id"),
                    "error": result.get("error"),
                    "error_type": result.get("error_type")
                })
        
        results["success"] = True
        return results
    
    def process_all_folders(self, base_folder: str) -> List[Dict]:
        """
        Process all folders in base folder
        
        Args:
            base_folder: Path to folder containing match folders
        
        Returns:
            List of processing results for each folder
        """
        base_path = Path(base_folder)
        
        if not base_path.exists():
            logger.error(f"Base folder does not exist: {base_folder}")
            return []
        
        # Get all subdirectories
        folders = [f for f in base_path.iterdir() if f.is_dir()]
        
        if not folders:
            logger.warning(f"No folders found in: {base_folder}")
            return []
        
        logger.info(f"Found {len(folders)} folders to process")
        logger.info("=" * 80)
        
        all_results = []
        
        for idx, folder_path in enumerate(folders, 1):
            logger.info(f"\n[{idx}/{len(folders)}] Processing folder: {folder_path.name}")
            logger.info("-" * 80)
            
            try:
                result = self.process_folder(str(folder_path))
                all_results.append(result)
            except Exception as e:
                logger.error(f"Error processing folder: {str(e)}")
                all_results.append({
                    "folder": folder_path.name,
                    "success": False,
                    "error": str(e),
                    "images_processed": 0
                })
        
        return all_results
    
    def save_results(self, results: List[Dict], output_file: str = "workflow_results.json"):
        """
        Save processing results to JSON file
        
        Args:
            results: List of processing results
            output_file: Output file path
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_folders": len(results),
            "successful_folders": sum(1 for r in results if r.get("success")),
            "total_images_processed": sum(r.get("images_processed", 0) for r in results),
            "total_images_success": sum(r.get("images_success", 0) for r in results),
            "total_images_failed": sum(r.get("images_failed", 0) for r in results),
            "results": results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\nResults saved to: {output_file}")
        logger.info(f"Summary:")
        logger.info(f"  Total folders: {summary['total_folders']}")
        logger.info(f"  Successful folders: {summary['successful_folders']}")
        logger.info(f"  Total images processed: {summary['total_images_processed']}")
        logger.info(f"  Successful images: {summary['total_images_success']}")
        logger.info(f"  Failed images: {summary['total_images_failed']}")
    
    def _find_images(self, folder_path: str) -> List[Path]:
        """
        Find all image files in folder.
        
        Supports Unicode file names (including Vietnamese characters) on Windows.
        Path.glob() in Python 3 handles Unicode correctly.
        """
        folder = Path(folder_path)
        image_files = []
        seen_files = set()  # Use absolute path strings to avoid duplicates on case-insensitive filesystems
        
        for ext in self.image_extensions:
            ext_clean = ext.strip()
            # Find lowercase - Path.glob() supports Unicode file names
            for img in folder.glob(f"*{ext_clean}"):
                img_path_str = str(img.resolve())  # Use absolute path
                if img_path_str not in seen_files:
                    image_files.append(img)
                    seen_files.add(img_path_str)
            # Find uppercase (may match same file on Windows)
            for img in folder.glob(f"*{ext_clean.upper()}"):
                img_path_str = str(img.resolve())  # Use absolute path
                if img_path_str not in seen_files:
                    image_files.append(img)
                    seen_files.add(img_path_str)
        
        return sorted(image_files)
