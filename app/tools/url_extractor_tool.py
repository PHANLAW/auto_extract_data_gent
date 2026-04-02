"""
URL Extractor Tool: Extract URL from images using Azure OpenAI Vision
"""

import cv2
import numpy as np
import base64
import os
import re
from typing import Optional, Tuple, Dict, List
from openai import AzureOpenAI
from google.cloud import vision
from google.oauth2 import service_account

from app.tools.base import BaseTool
from app.core.config import get_settings
from app.core.prompt_loader import prompt_loader
from app.core.logging_config import logger

settings = get_settings()


class URLExtractorTool(BaseTool):
    """Tool for extracting URLs from images"""
    
    def __init__(self, client: AzureOpenAI):
        """
        Initialize URL extractor tool
        
        Args:
            client: AzureOpenAI client instance
        """
        super().__init__(
            name="extract_url",
            description="Extract URL from browser address bar in image"
        )
        self.client = client
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT

        # Initialize Google Cloud Vision client (lazy)
        self._gcv_client: Optional[vision.ImageAnnotatorClient] = None
        
        # Load prompt configuration
        prompt_config = prompt_loader.load_prompt("url_extraction")
        if prompt_config:
            self.use_crop = prompt_config.get("image_processing", {}).get("use_crop", settings.USE_CROP)
            self.crop_ratio = prompt_config.get("image_processing", {}).get("crop_ratio", settings.CROP_RATIO)
        else:
            self.use_crop = settings.USE_CROP
            self.crop_ratio = settings.CROP_RATIO
    
    def validate(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Validate inputs"""
        from pathlib import Path
        image_path = kwargs.get("image_path")
        if not image_path:
            return False, "image_path is required"
        # Use Path.exists() for better Unicode support on Windows
        if not Path(image_path).exists():
            return False, f"Image file not found: {image_path}"
        return True, None
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # ---------- Google Cloud Vision helpers ----------

    def _get_gcv_client(self) -> Optional[vision.ImageAnnotatorClient]:
        """Lazy init Google Cloud Vision client using service-account.json."""
        if self._gcv_client is not None:
            return self._gcv_client
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GCV_SERVICE_ACCOUNT_FILE
            )
            self._gcv_client = vision.ImageAnnotatorClient(credentials=credentials)
            logger.info("Initialized Google Cloud Vision client")
            return self._gcv_client
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Vision client: {e}")
            return None

    def is_web_browser_image(self, image_path: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if image is a web browser screenshot with address bar.
        
        Returns:
            (is_web, error_message)
            - is_web: True if image is web browser, False otherwise
            - error_message: Error message if detection failed, None if successful
        """
        try:
            # Load prompt for web image detection
            prompt_text = prompt_loader.get_prompt_text("web_image_detection")
            if not prompt_text:
                # Fallback prompt if YAML not found
                prompt_text = (
                    "Bạn là hệ thống phân loại ảnh chụp màn hình. "
                    "Xác định xem ảnh này có phải là ảnh chụp màn hình trình duyệt web (web browser) có thanh địa chỉ (address bar) hay không. "
                    "Nếu là ảnh web có thanh address bar: trả về 'YES'. "
                    "Nếu KHÔNG phải ảnh web (ví dụ: ảnh app mobile, ảnh desktop không có trình duyệt): trả về 'NO'. "
                    "Chỉ trả về YES hoặc NO, không giải thích."
                )
            
            # Encode image
            base64_image = self.encode_image(image_path)
            
            # Get model config
            model_config = prompt_loader.get_model_config("web_image_detection")
            max_tokens = model_config.get("max_tokens", 10)
            temperature = model_config.get("temperature", 0.0)
            
            # Call Azure OpenAI Vision API
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30.0
            )
            
            answer = (response.choices[0].message.content or "").strip().upper()
            
            # Check answer
            if answer == "YES":
                return True, None
            elif answer == "NO":
                return False, None
            else:
                # If answer is unclear, default to False (not web) to be safe
                logger.warning(f"Unclear web detection answer: {answer}, treating as non-web")
                return False, None
                
        except Exception as e:
            logger.error(f"Error detecting web image: {e}")
            # On error, default to False (not web) to avoid processing non-web images
            return False, f"Error detecting web image: {str(e)}"
    
    def _get_gcv_text(self, image_path: str) -> Optional[str]:
        """
        Get raw text from GCV OCR (for validation step).
        
        Returns:
            Raw text string if found, otherwise None.
        """
        client = self._get_gcv_client()
        if client is None:
            return None

        try:
            with open(image_path, "rb") as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)

            if response.error.message:
                logger.error(f"GCV OCR error: {response.error.message}")
                return None

            full_text = response.full_text_annotation
            if not full_text or not full_text.text:
                return None

            return full_text.text
        except Exception as e:
            logger.error(f"GCV OCR exception: {e}")
            return None
    
    def extract_url_with_gcv(self, image_path: str) -> Optional[str]:
        """
        Use Google Cloud Vision OCR to quickly extract URL text from image.

        Returns:
            URL string if found, otherwise None.
        """
        client = self._get_gcv_client()
        if client is None:
            return None

        try:
            with open(image_path, "rb") as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)

            if response.error.message:
                logger.error(f"GCV OCR error: {response.error.message}")
                return None

            # Use full_text_annotation để lấy text và vị trí
            full_text = response.full_text_annotation
            if not full_text or not full_text.text:
                return None

            text = full_text.text
            lower_text = text.lower()
            
            # Xác định có chữ "Không bảo mật" (hoặc tương đương) hay không
            # Nếu có, ưu tiên dùng http://, ngược lại dùng https://
            is_insecure = (
                "không bảo mật" in lower_text
                or "khong bao mat" in lower_text
                or "not secure" in lower_text
            )

            # Tìm URL trong text, ưu tiên URL ở trên cùng (address bar)
            # Sử dụng vị trí text để chỉ lấy URL ở trên cùng của ảnh crop
            url_regex = re.compile(
                r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*)"
            )
            
            # Lấy tất cả text blocks với vị trí của chúng
            url_candidates = []
            
            # Duyệt qua các pages, blocks, paragraphs, words để tìm URL ở trên cùng
            if full_text.pages:
                for page in full_text.pages:
                    if page.blocks:
                        for block in page.blocks:
                            if block.bounding_box:
                                # Lấy Y coordinate của block (vị trí trên cùng = Y nhỏ nhất)
                                vertices = block.bounding_box.vertices
                                if vertices:
                                    y_coord = min(v.y for v in vertices if v.y)
                                    
                                    # Lấy text trong block này
                                    block_text = ""
                                    if block.paragraphs:
                                        for para in block.paragraphs:
                                            if para.words:
                                                for word in para.words:
                                                    if word.symbols:
                                                        block_text += "".join(s.text for s in word.symbols)
                                                    block_text += " "
                                    
                                    # Tìm URL trong block text này
                                    matches = url_regex.finditer(block_text)
                                    for match in matches:
                                        candidate = match.group(0).strip()
                                        # Validate domain hợp lý
                                        if candidate.startswith(("http://", "https://")):
                                            url_candidates.append((y_coord, candidate, True))  # (y_pos, url, has_scheme)
                                        else:
                                            domain_part = candidate.split('/')[0] if '/' in candidate else candidate
                                            parts = domain_part.split('.')
                                            if len(parts) >= 2 and len(parts[-1]) >= 2:
                                                domain_name = parts[0] if parts else ""
                                                if len(domain_name) >= 3:
                                                    url_candidates.append((y_coord, candidate, False))  # (y_pos, url, has_scheme)
            
            if not url_candidates:
                # Fallback: tìm URL trong toàn bộ text nếu không có vị trí
                matches = list(url_regex.finditer(text))
                for match in matches:
                    candidate = match.group(0).strip()
                    if candidate.startswith(("http://", "https://")):
                        url_candidates.append((0, candidate, True))
                    else:
                        domain_part = candidate.split('/')[0] if '/' in candidate else candidate
                        parts = domain_part.split('.')
                        if len(parts) >= 2 and len(parts[-1]) >= 2:
                            domain_name = parts[0] if parts else ""
                            if len(domain_name) >= 3:
                                url_candidates.append((0, candidate, False))
            
            if not url_candidates:
                return None
            
            # Ưu tiên: 1) URL có scheme, 2) URL ở trên cùng (Y nhỏ nhất)
            # Sort: has_scheme DESC, y_coord ASC
            url_candidates.sort(key=lambda x: (not x[2], x[0]))
            raw_url = url_candidates[0][1]

            # Nếu đã có scheme thì có thể cần sửa lại theo is_insecure
            if raw_url.startswith("http://") or raw_url.startswith("https://"):
                if is_insecure:
                    # Ép về http:// nếu Chrome báo "Không bảo mật"
                    raw_url = re.sub(
                        r"^https://",
                        "http://",
                        raw_url,
                        flags=re.IGNORECASE,
                    )
            else:
                # Chưa có scheme, tự thêm theo is_insecure
                scheme = "http://" if is_insecure else "https://"
                raw_url = scheme + raw_url

            url = self.normalize_url(raw_url)
            logger.info(f"GCV extracted URL candidate: {url}")
            return url
        except Exception as e:
            logger.error(f"GCV OCR exception: {e}")
            return None
    
    def validate_url_from_ocr(
        self,
        ocr_text: str,
        cropped_image_path: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Validate and extract correct URL from OCR text and cropped address bar image.
        This ensures we only get URL from address bar, not from watermark/logo/text.
        
        Args:
            ocr_text: Text extracted by GCV OCR (may contain multiple texts)
            cropped_image_path: Path to cropped image (address bar region)
        
        Returns:
            (validated_url, error_message)
        """
        try:
            # Load prompt for URL validation
            prompt_text = prompt_loader.get_prompt_text("url_validation")
            if not prompt_text:
                # Fallback prompt
                prompt_text = (
                    "BẠN LÀ HỆ THỐNG XÁC THỰC URL CHUYÊN NGHIỆP. "
                    "NHIỆM VỤ: Xác định URL CHÍNH XÁC từ thanh địa chỉ (address bar) trong ảnh. "
                    "ĐẦU VÀO: "
                    "- ẢNH: Phần trên cùng của trình duyệt đã được cắt (chứa address bar) "
                    "- OCR_TEXT: Text đã được OCR đọc từ ảnh này "
                    "QUY TRÌNH: "
                    "1. Quan sát ảnh để xác định vị trí thanh địa chỉ "
                    "2. So sánh OCR_TEXT với những gì bạn thấy TRỰC TIẾP trong ảnh "
                    "3. Chỉ chọn URL nếu URL đó THỰC SỰ HIỂN THỊ trong thanh địa chỉ "
                    "4. Nếu OCR_TEXT có URL đúng → sử dụng, nếu sai → đọc lại từ ảnh "
                    "ĐỊNH DẠNG: Trả về URL duy nhất hoặc 'NONE' nếu không tìm được. "
                    "Không giải thích, không text khác."
                )
            
            # Append OCR text to prompt
            full_prompt = f"{prompt_text}\n\nOCR_TEXT đã đọc được:\n{ocr_text}\n\nHãy xác định URL chính xác từ thanh địa chỉ trong ảnh."
            
            # Encode cropped image
            base64_image = self.encode_image(cropped_image_path)
            
            # Get model config
            model_config = prompt_loader.get_model_config("url_validation")
            max_tokens = model_config.get("max_tokens", 300)
            temperature = model_config.get("temperature", 0.0)
            
            # Call Azure OpenAI Vision API
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": full_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=60.0
            )
            
            answer = (response.choices[0].message.content or "").strip()
            
            # Check if answer is NONE
            if answer.upper().startswith("NONE") or not answer:
                return None, "No valid URL found in address bar"
            
            # Normalize and validate URL
            url = self.normalize_url(answer)
            if not self.validate_url(url):
                return None, f"Invalid URL format: {url}"
            
            logger.info(f"Validated URL from OCR text: {url}")
            return url, None
            
        except Exception as e:
            logger.error(f"Error validating URL from OCR: {e}")
            return None, f"Error validating URL: {str(e)}"
    
    def choose_best_detected_link(
        self,
        ocr_url: str,
        candidates: List[Dict],
        image_path: str,
    ) -> Tuple[Optional[str], Optional[str], float]:
        """
        Use Azure OpenAI Vision to choose best detected_link from candidate list.
        
        Returns:
            (detected_link_id, matched_url, confidence_score)
        """
        if not candidates:
            return None, None, 0.0
        
        try:
            # Base prompt text from YAML
            base_prompt = prompt_loader.get_prompt_text("detected_link_match") or ""
            
            # Append dynamic context (OCR_URL + candidate list)
            lines = [
                base_prompt.strip(),
                "",
                f"OCR_URL: {ocr_url}",
                "",
                "CANDIDATE_URLS:",
            ]
            for idx, item in enumerate(candidates, start=1):
                cid = item.get("id")
                curl = item.get("url")
                if not cid or not curl:
                    continue
                lines.append(f"{idx}) id={cid}, url={curl}")
            lines.append("")
            prompt_text = "\n".join(lines)
            
            # Encode image (use FULL ORIGINAL image, not cropped)
            # This ensures agent can see the complete address bar and make accurate decision
            base64_image = self.encode_image(image_path)
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=64,
                temperature=0.0,
                timeout=60.0,
            )
            answer = (response.choices[0].message.content or "").strip()
            if answer.upper().startswith("NONE"):
                return None, None, 0.0
            if answer.startswith("DETECTED_LINK_ID="):
                detected_id = answer.split("=", 1)[1].strip()
                # Find matched URL in candidates
                for item in candidates:
                    if item.get("id") == detected_id:
                        return detected_id, item.get("url"), 1.0
            return None, None, 0.0
        except Exception as e:
            logger.error(f"choose_best_detected_link error: {e}")
            return None, None, 0.0
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format"""
        if not url:
            return False
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize and clean URL
        
        Rules:
        - Remove markdown code blocks, labels, whitespace
        - Add https:// if missing
        - Add trailing slash to domain-only URLs (e.g., https://lacboxoi.com -> https://lacboxoi.com/)
        - Keep trailing slash if URL already has path
        """
        if not url:
            return ""
        
        url = url.replace("```", "").replace("URL:", "").replace("url:", "").strip()
        url = url.replace("\n", "").replace("\r", "").replace(" ", "")
        
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Add trailing slash to domain-only URLs (no path, no query, no fragment)
        # Example: https://lacboxoi.com -> https://lacboxoi.com/
        # But keep: https://lacboxoi.com/path -> https://lacboxoi.com/path
        if url and not url.endswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            # If path is empty or just "/", and no query/fragment, add trailing slash
            if not parsed.path or parsed.path == "/":
                if not parsed.query and not parsed.fragment:
                    url = url.rstrip("/") + "/"
        
        return url
    
    def execute(self, **kwargs) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract URL from image
        
        Args:
            image_path: Path to image file
        
        Returns:
            Tuple of (url, error_message)
        """
        image_path = kwargs.get("image_path")
        
        # Validate
        is_valid, error = self.validate(**kwargs)
        if not is_valid:
            return None, error
        
        try:
            # Step 0: Check if image is a web browser screenshot
            # Only process web browser images, skip app screenshots
            is_web, web_detect_error = self.is_web_browser_image(image_path)
            if not is_web:
                error_msg = web_detect_error or "Image is not a web browser screenshot (no address bar detected)"
                logger.info(f"Skipping non-web image: {image_path} - {error_msg}")
                # Return special error message to indicate this is a non-web image
                return None, f"NOT_WEB_IMAGE: {error_msg}"
            
            # Crop image if needed (ONLY for URL extraction, NOT for upload)
            # The cropped image is temporary and will be deleted after use.
            # The original image_path remains unchanged and will be used for upload.
            if self.use_crop:
                # Use np.fromfile + cv2.imdecode to support Unicode paths on Windows
                img_array = np.fromfile(image_path, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is None:
                    return None, "Cannot read image"
                
                height, width = img.shape[:2]
                crop_height = int(height * self.crop_ratio)
                address_bar_region = img[0:crop_height, 0:width]

                # UPSCALE STEP: Chỉ upscale khi crop_height quá nhỏ để tránh làm mất URL
                # Giới hạn scale factor tối đa 3x để tránh làm mất chất lượng và làm mất URL
                try:
                    if crop_height > 0 and crop_height < 400:
                        # Chỉ upscale khi crop_height < 400px để đảm bảo URL đủ rõ
                        # Target: đưa lên tối thiểu 400px nhưng không quá 3x scale
                        target_height = min(400, crop_height * 3)
                        scale = target_height / float(crop_height)
                        if 1.0 < scale <= 3.0:  # Chỉ upscale nếu scale hợp lý (1-3x)
                            upscaled_width = int(width * scale)
                            upscaled_height = int(crop_height * scale)
                            address_bar_region = cv2.resize(
                                address_bar_region,
                                (upscaled_width, upscaled_height),
                                interpolation=cv2.INTER_CUBIC
                            )
                            logger.info(f"Upscaled cropped region from {crop_height}px to {upscaled_height}px (scale={scale:.2f}x)")
                except Exception as e:
                    logger.warning(f"Upscale failed, using original crop: {e}")
                    pass
                
                import tempfile
                import os
                temp_fd, temp_file = tempfile.mkstemp(suffix='.png', prefix='temp_crop_')
                os.close(temp_fd)
                success, encoded_img = cv2.imencode('.png', address_bar_region, [cv2.IMWRITE_PNG_COMPRESSION, 1])
                if success:
                    encoded_img.tofile(temp_file)
                else:
                    return None, "Cannot encode cropped image"
                image_to_process = temp_file  # Temporary cropped image for URL extraction
            else:
                image_to_process = image_path  # Use original image
            
            # First attempt: Google Cloud Vision OCR for quick text extraction
            # Get OCR text (may contain multiple texts including watermark/logo)
            gcv_text = self._get_gcv_text(image_to_process)
            if gcv_text:
                # Step: Validate URL from OCR text + cropped image using Azure agent
                # This ensures we only get URL from address bar, not from watermark/logo
                validated_url, validation_error = self.validate_url_from_ocr(
                    ocr_text=gcv_text,
                    cropped_image_path=image_to_process
                )
                if validated_url:
                    logger.info(f"Validated URL from GCV OCR: {validated_url}")
                    return validated_url, None
                else:
                    logger.info(f"GCV OCR text did not contain valid address bar URL, falling back to Azure OCR")
                    # Continue to Azure fallback below

            # Fallback: Azure OpenAI Vision via agent
            # Encode image
            base64_image = self.encode_image(image_to_process)
            
            # Clean up temp file
            if self.use_crop:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            # Load prompt
            prompt_text = prompt_loader.get_prompt_text("url_extraction")
            if not prompt_text:
                prompt_text = (
                    "BẠN LÀ MỘT HỆ THỐNG OCR CHUYÊN NGHIỆP VÀ CHÍNH XÁC để trích xuất URL từ ảnh chụp màn hình trình duyệt. "
                    "NHIỆM VỤ: Trích xuất URL ĐẦY ĐỦ và CHÍNH XÁC 100% từ thanh địa chỉ (address bar) ở trên cùng của trình duyệt. "
                    "QUY TRÌNH OCR: "
                    "1. Đọc từ TRÁI SANG PHẢI, từng ký tự một, ĐỌC CHẬM VÀ CẨN THẬN, KHÔNG BỎ SÓT BẤT KỲ KÝ TỰ NÀO ở BẤT KỲ VỊ TRÍ NÀO. "
                    "2. PHÂN BIỆT RÕ RÀNG chữ HOA và chữ THƯỜNG - trong URL chúng KHÁC NHAU hoàn toàn. "
                    "3. PHÂN BIỆT CHÍNH XÁC: 'U' HOA vs 'A' HOA vs 'u' thường vs 'a' thường; "
                    "   'd' thường (dễ bị bỏ sót), 'r' thường, 'l' thường vs 'i' thường vs '1'; 'O' HOA vs '0'; 'I' HOA vs '1' vs 'l'. "
                    "4. ĐỌC LẠI URL 3 LẦN để đảm bảo không thiếu ký tự ở giữa URL, không nhầm, phân biệt đúng HOA/THƯỜNG. "
                    "5. Đếm số ký tự để xác nhận không bỏ sót, đặc biệt chú ý các ký tự ở giữa URL như 'd', 'r', 'l'. "
                    "Chỉ trả về URL duy nhất, không có text nào khác, không có giải thích, không có dấu ngoặc kép. "
                    "Nếu URL không có http:// hoặc https://, hãy thêm https:// vào đầu. "
                    "GIỮ NGUYÊN chữ HOA và chữ THƯỜNG như trong ảnh. "
                    "CẢNH BÁO: Các ký tự ở GIỮA URL như 'd', 'r', 'l' rất dễ bị BỎ SÓT - hãy đọc CHẬM và CẨN THẬN. "
                    "Hãy hoạt động như một hệ thống OCR chuyên nghiệp với độ chính xác 100%."
                )
            
            # Get model config
            model_config = prompt_loader.get_model_config("url_extraction")
            max_tokens = model_config.get("max_tokens", 300)
            temperature = model_config.get("temperature", 0.1)
            
            # Call Azure OpenAI Vision API
            # Note: Azure OpenAI client has built-in retry for 429 errors with exponential backoff
            # We also add delay between requests in workflow_service to prevent rate limiting
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt_text
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=60.0  # 60 second timeout
                )
            except Exception as e:
                # Check if it's a rate limit error (429)
                error_str = str(e).lower()
                if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
                    # Add additional delay after 429 error
                    import time
                    retry_delay = settings.AZURE_OPENAI_RETRY_DELAY
                    logger.warning(f"Rate limit (429) detected, waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    # Retry once more after delay
                    response = self.client.chat.completions.create(
                        model=self.deployment_name,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt_text
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=60.0
                    )
                else:
                    # Re-raise if it's not a rate limit error
                    raise
            
            # Extract URL
            url = response.choices[0].message.content.strip()
            url = self.normalize_url(url)
            
            # Validate URL
            if not self.validate_url(url):
                return None, f"Invalid URL format: {url}"
            
            logger.info(f"Extracted URL: {url}")
            return url, None
            
        except Exception as e:
            logger.error(f"Error extracting URL: {e}")
            return None, f"Error extracting URL: {str(e)}"
    
    def get_schema(self) -> Dict:
        """Get tool schema"""
        schema = super().get_schema()
        schema["parameters"] = {
            "image_path": {
                "type": "string",
                "description": "Path to the image file",
                "required": True
            }
        }
        return schema
