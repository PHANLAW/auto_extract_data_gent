"""
Image Processing Agent: Orchestrate URL extraction and API calls
"""

import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from difflib import SequenceMatcher
from app.tools.tool_manager import tool_manager
from app.tools.url_extractor_tool import URLExtractorTool
from app.tools.api_tools import DetectLinkTool, UploadImageTool
from app.utils.error_handler import ErrorHandler
from app.core.logging_config import logger, sanitize_log_message


class ImageProcessingAgent:
    """
    AI Agent for processing images:
    1. Extract URL from image
    2. Call API to get detected_link_id
    3. Upload image with detected_link_id
    """
    
    def __init__(
        self,
        url_extractor_tool: URLExtractorTool,
        detect_link_tool: DetectLinkTool,
        upload_image_tool: UploadImageTool,
        error_handler: ErrorHandler
    ):
        """
        Initialize the agent
        
        Args:
            url_extractor_tool: URLExtractorTool instance
            detect_link_tool: DetectLinkTool instance
            upload_image_tool: UploadImageTool instance
            error_handler: ErrorHandler instance
        """
        self.url_extractor_tool = url_extractor_tool
        self.detect_link_tool = detect_link_tool
        self.upload_image_tool = upload_image_tool
        self.error_handler = error_handler
        
        # Register tools
        tool_manager.register_tool(url_extractor_tool)
        tool_manager.register_tool(detect_link_tool)
        tool_manager.register_tool(upload_image_tool)
    
    def process_images_batch(
        self,
        images: List[Dict]
    ) -> List[Dict]:
        """
        Process a small batch of images (max 2) in a single agent call.
        
        Each item in images should have:
            {
                "id": int,              # Stable index of image in folder
                "image_path": str,      # Path to image file
                "match_name": str,      # Match name
                "sport_id": int         # Sport ID (reused for all images in folder)
            }
        
        Returns:
            List of result dicts in the SAME ORDER as input, each extended with "image_id".
        """
        results: List[Dict] = []
        
        for item in images:
            image_id = item.get("id")
            image_path = item.get("image_path")
            match_name = item.get("match_name")
            sport_id = item.get("sport_id")
            
            # Reuse existing single-image workflow to keep logic identical
            result = self.process_image(
                image_path=image_path,
                match_name=match_name,
                sport_id=sport_id
            )
            # Attach stable image id so caller can keep ordering
            result["image_id"] = image_id
            results.append(result)
        
        return results
    
    def process_image(
        self,
        image_path: str,
        match_name: str,
        sport_id: int
    ) -> Dict:
        """
        Process a single image through the complete workflow
        
        Args:
            image_path: Path to image file
            match_name: Name of the match (for error handling)
            sport_id: Sport ID from API
        
        Returns:
            Dictionary with processing result:
            {
                "success": bool,
                "url": str or None,
                "detected_link_id": int or None,
                "error": str or None,
                "error_type": str or None
            }
        """
        image_name = os.path.basename(image_path)
        result = {
            "success": False,
            "url": None,
            "detected_link_id": None,
            "error": None,
            "error_type": None
        }
        
        # Step 1: Extract URL from image
        url, extract_error = self.url_extractor_tool.execute(image_path=image_path)
        
        if extract_error or not url:
            error_msg = extract_error or "No URL extracted"
            
            # Check if this is a non-web image (should be skipped, not retried)
            if error_msg.startswith("NOT_WEB_IMAGE:"):
                result["error"] = error_msg.replace("NOT_WEB_IMAGE: ", "")
                result["error_type"] = "not_web_image"
                # Sanitize error message for logging to avoid UnicodeEncodeError
                safe_error_msg = sanitize_log_message(error_msg)
                logger.info(f"Skipping non-web image: {image_name} - {safe_error_msg}")
                
                # Write to retry file with special error_type for tracking
                self.error_handler.write_failed_extraction(
                    match_name=match_name,
                    image_name=image_name,
                    error=error_msg.replace("NOT_WEB_IMAGE: ", ""),
                    error_type="not_web_image"
                )
            else:
                result["error"] = error_msg
                result["error_type"] = "extract_error"
                # Sanitize error message for logging to avoid UnicodeEncodeError
                safe_error_msg = sanitize_log_message(error_msg)
                logger.warning(f"Failed to extract URL from {image_name}: {safe_error_msg}")
                
                # Write to retry file for later retry
                self.error_handler.write_failed_extraction(
                    match_name=match_name,
                    image_name=image_name,
                    error=error_msg
                )
            
            return result
        
        result["url"] = url
        logger.info(f"Extracted URL from {image_name}: {url}")
        
        # Step 2: Detect link and get detected_link_id
        detected_link_id, detect_error = self.detect_link_tool.execute(
            url=url,
            sport_id=sport_id
        )
        
        # Rescue flow if check_exists không tìm thấy ID nhưng cũng không báo lỗi
        if not detected_link_id and not detect_error:
            try:
                api_client = getattr(self.detect_link_tool, "api_client", None)
                if api_client is not None:
                    parsed = urlparse(url)
                    bare_domain = parsed.netloc.replace("www.", "", 1)
                    
                    # 1) Lấy domain_id
                    domain_id, domain_err = api_client.get_domain_id(bare_domain)
                    if domain_id and not domain_err:
                        # 2) Lấy danh sách detected_links theo sport_id + domain_id
                        detected_links, list_err = api_client.list_detected_links(
                            sport_id=str(sport_id),
                            domain_id=domain_id,
                        )
                        if not list_err and detected_links:
                            # detected_links là danh sách từ list_detected_links(domain_id + sport_id)
                            # Mỗi item có format: {"id": "...", "url": "...", ...}
                            
                            # 2.1) Thử so khớp similarity trước
                            # Tính similarity giữa URL OCR với từng URL trong detected_links
                            best_id, best_url, best_score = self._find_best_similarity_match(
                                ocr_url=url,
                                candidates=detected_links,  # Danh sách từ list_detected_links(domain_id + sport_id)
                            )
                            if best_id and best_score >= 0.85:
                                # Ghi log guess theo similarity vào warning_matches.json
                                self.error_handler.write_warning_match(
                                    match_name=match_name,
                                    image_name=image_name,
                                    url=url,
                                    error=(
                                        f"detect_guess_similarity: matched {best_id} "
                                        f"from {best_url} with similarity={best_score:.3f}"
                                    ),
                                    error_type="detect_guess_similarity",
                                )
                                detected_link_id = best_id
                            else:
                                # 2.2) Nếu similarity không đủ (< 85%), dùng agent để chọn từ list
                                # Agent nhận: OCR URL + danh sách detected_links + ảnh gốc (full)
                                best_id, best_url, best_conf = self.url_extractor_tool.choose_best_detected_link(  # type: ignore[attr-defined]
                                    ocr_url=url,
                                    candidates=detected_links,  # Danh sách từ list_detected_links(domain_id + sport_id)
                                    image_path=image_path,  # Ảnh gốc (full) để agent xem đầy đủ
                                )
                                if best_id:
                                    # Ghi log guess theo agent vào warning_matches.json
                                    self.error_handler.write_warning_match(
                                        match_name=match_name,
                                        image_name=image_name,
                                        url=url,
                                        error=(
                                            f"detect_guess_by_agent: matched {best_id} "
                                            f"from {best_url} with confidence={best_conf:.3f}"
                                        ),
                                        error_type="detect_guess_by_agent",
                                    )
                                    detected_link_id = best_id
            except Exception as e:
                safe_msg = sanitize_log_message(str(e))
                logger.warning(f"Rescue flow for detected_link_id failed for {image_name}: {safe_msg}")
        
        if detect_error or not detected_link_id:
            # Error: No detected_link_id - write to retry file
            self.error_handler.write_failed_url(
                match_name=match_name,
                image_name=image_name,
                url=url,
                error=detect_error or "No detected_link_id in response"
            )
            result["error"] = detect_error or "No detected_link_id in response"
            result["error_type"] = "detect_error"
            # Sanitize error message for logging
            safe_error_msg = sanitize_log_message(detect_error or "No detected_link_id in response")
            logger.warning(f"Failed to detect link for {image_name}: {safe_error_msg}")
            return result
        
        result["detected_link_id"] = detected_link_id
        logger.info(f"Detected link ID for {image_name}: {detected_link_id}")
        
        # Step 3: Upload image (using ORIGINAL full image, not cropped)
        # Note: The image_path here is the original full image file.
        # The cropped image (if used) was only for URL extraction and has been deleted.
        # We also pass the extracted URL so the upload layer can:
        #   - Parse domain
        #   - Rename file to "<detected_link_id>_<domain>.<ext>" to avoid collisions
        upload_success, upload_error = self.upload_image_tool.execute(
            image_path=image_path,  # Original full image
            detected_link_id=detected_link_id,
            url=url
        )
        
        if not upload_success:
            result["error"] = upload_error
            result["error_type"] = "upload_error"
            # Sanitize error message for logging
            safe_error_msg = sanitize_log_message(upload_error or "Upload failed")
            logger.warning(f"Failed to upload {image_name}: {safe_error_msg}")
            return result
        
        # Success!
        result["success"] = True
        logger.info(f"Successfully processed {image_name}")
        return result

    # ==========================
    # Helper methods
    # ==========================

    def _find_best_similarity_match(
        self,
        ocr_url: str,
        candidates: List[Dict],
    ) -> Tuple[Optional[str], Optional[str], float]:
        """
        Find best match by similarity between OCR URL and candidate URLs.
        
        Returns:
            (best_detected_link_id, best_url, best_score)
        """
        if not ocr_url or not candidates:
            return None, None, 0.0
        
        best_id: Optional[str] = None
        best_url: Optional[str] = None
        best_score: float = 0.0
        
        for item in candidates:
            candidate_url = item.get("url")
            candidate_id = item.get("id")
            if not candidate_url or not candidate_id:
                continue
            score = SequenceMatcher(None, ocr_url, candidate_url).ratio()
            if score > best_score:
                best_score = score
                best_id = candidate_id
                best_url = candidate_url
        
        return best_id, best_url, best_score
