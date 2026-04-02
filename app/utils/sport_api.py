"""
Sport API Client: Handle API calls for league_id, sport_id, detected_link_id, and image upload
"""

import requests
from typing import Optional, Tuple, Dict, List
from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()


class SportAPIClient:
    """Client for interacting with Sport API"""
    
    def __init__(self, base_url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize API client
        
        Args:
            base_url: Base URL of the API (defaults to config)
            username: Username for login (defaults to config)
            password: Password for login (defaults to config)
        """
        self.base_url = (base_url or settings.SPORT_API_BASE_URL).rstrip('/')
        self.username = username or settings.SPORT_API_USERNAME
        self.password = password or settings.SPORT_API_PASSWORD
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # Auto login if credentials provided
        if self.username and self.password:
            self.login()
    
    def login(self) -> Tuple[bool, Optional[str]]:
        """
        Login to get access token
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            endpoint = f"{self.base_url}/api/v1/auth/login"
            
            # Login uses form-urlencoded, not JSON
            data = {
                "username": self.username,
                "password": self.password
            }
            
            login_headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(
                endpoint,
                data=data,
                headers=login_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                
                if self.access_token:
                    # Update headers with access token
                    self.headers["Authorization"] = f"Bearer {self.access_token}"
                    logger.info("Successfully logged in and obtained access token")
                    return True, None
                else:
                    return False, "No access_token in response"
            else:
                return False, f"Login failed {response.status_code}: {response.text}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during login: {e}")
            return False, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            return False, f"Unexpected error: {str(e)}"
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid access token
        
        Returns:
            True if authenticated, False otherwise
        """
        if not self.access_token:
            if self.username and self.password:
                success, error = self.login()
                if not success:
                    logger.error(f"Cannot authenticate: {error}")
                    return False
            else:
                logger.error("No credentials provided for authentication")
                return False
        return True
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with automatic authentication and 401 retry
        
        Args:
            method: HTTP method (get, post, etc.)
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments for requests
        
        Returns:
            Response object
        """
        if not self._ensure_authenticated():
            raise Exception("Not authenticated")
        
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        func = getattr(requests, method.lower())
        
        response = func(url, headers=self.headers, **kwargs)
        
        # Handle 401 Unauthorized - try to re-login and retry
        if response.status_code == 401:
            logger.warning("Got 401, attempting to re-login...")
            if self.username and self.password:
                success, error = self.login()
                if success:
                    # Retry request with new token
                    response = func(url, headers=self.headers, **kwargs)
                else:
                    logger.error(f"Re-login failed: {error}")
        
        return response
    
    def get_league_id(self, league_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get league ID by league name
        
        Args:
            league_name: Name of the league (e.g., "PL 25_26")
        
        Returns:
            Tuple of (league_id, error_message)
            league_id is UUID string
        """
        if not self._ensure_authenticated():
            return None, "Not authenticated"
        
        try:
            params = {
                "name": league_name,
                "page": 1,
                "page_size": 10
            }
            
            response = self._make_request("get", "/api/v1/leagues/", params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # Response format: {"data": [...], "meta": {...}}
                leagues = data.get("data", [])
                
                if leagues and len(leagues) > 0:
                    # Lấy phần tử đầu tiên
                    league_id = leagues[0].get("id")
                    if league_id:
                        logger.info(f"Got league_id: {league_id} for league: {league_name}")
                        return league_id, None
                    else:
                        return None, f"No id in league response: {leagues[0]}"
                else:
                    return None, f"No leagues found with name: {league_name}"
            else:
                return None, f"API error {response.status_code}: {response.text}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting league_id: {e}")
            return None, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error getting league_id: {e}")
            return None, f"Unexpected error: {str(e)}"
    
    def get_sport_id(self, match_name: str, start_time: str, league: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get sport_id by calling league API first, then sport API
        
        Args:
            match_name: Name of the match
            start_time: Start time in format "yyyy-mm-dd hh:mm"
            league: League name
        
        Returns:
            Tuple of (sport_id, error_message)
            sport_id is UUID string
        """
        try:
            # Step 1: Get league_id
            league_id, league_error = self.get_league_id(league)
            if league_error or not league_id:
                return None, f"Cannot get league_id: {league_error}"
            
            # Step 2: Get sport_id using league_id, match_name, start_time
            params = {
                "league_id": league_id,
                "match_name": match_name,
                "start_time": start_time,  # Format: YYYY-MM-DD HH:MM
                "page": 1,
                "page_size": 10
            }
            
            response = self._make_request("get", "/api/v1/sports/", params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # Response format: {"data": [...], "meta": {...}}
                sports = data.get("data", [])
                
                if sports and len(sports) > 0:
                    # Lấy phần tử đầu tiên
                    sport_id = sports[0].get("id")
                    if sport_id:
                        logger.info(f"Got sport_id: {sport_id} for match: {match_name}")
                        return sport_id, None
                    else:
                        return None, f"No id in sport response: {sports[0]}"
                else:
                    return None, f"No sports found with league_id={league_id}, match_name={match_name}, start_time={start_time}"
            else:
                return None, f"API error {response.status_code}: {response.text}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting sport_id: {e}")
            return None, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error getting sport_id: {e}")
            return None, f"Unexpected error: {str(e)}"
    
    def check_exists(self, url: str, sport_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Check if detected link exists for given URL and sport_id.
        
        Logic (để xử lý case Google/Chrome ẩn hoặc bỏ 'www'):
        - Bước 1: Check URL đúng như agent đọc được (không tự ý đổi http/https)
        - Bước 2: Nếu host KHÔNG bắt đầu bằng 'www.', check thêm 1 lần nữa với host 'www.<host>'
        - Nếu không URL nào có detected_link_id -> trả về (None, None)
        - Nếu chỉ 1 URL có detected_link_id -> dùng ID đó
        - Nếu CẢ HAI có detected_link_id KHÁC NHAU -> trả về lỗi "ambiguous" để ghi vào retry
        
        Args:
            url: URL extracted from image (đã normalize, giữ nguyên http/https)
            sport_id: Sport ID (UUID string)
        
        Returns:
            Tuple of (detected_link_id, error_message)
            detected_link_id is UUID string if exists, None nếu không tìm thấy
            error_message is None nếu OK, hoặc message nếu có lỗi/ambiguous
        """
        try:
            from urllib.parse import urlparse, urlunparse
            
            # Build URL variants: [original, original+www] (nếu cần)
            url_variants = []
            if url:
                url_variants.append(url)
                parsed = urlparse(url)
                # Nếu host tồn tại và KHÔNG bắt đầu bằng 'www.', tạo thêm bản có 'www.'
                if parsed.netloc and not parsed.netloc.lower().startswith("www."):
                    www_netloc = "www." + parsed.netloc
                    url_with_www = urlunparse((
                        parsed.scheme,
                        www_netloc,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    ))
                    if url_with_www not in url_variants:
                        url_variants.append(url_with_www)
            
            detected_results: Dict[str, str] = {}
            
            # Helper: check một list URL và ghi kết quả vào detected_results
            def _check_variant_list(variant_list):
                nonlocal detected_results
                for candidate_url in variant_list:
                    params = {
                        "url": candidate_url,
                        "sport_id": sport_id
                    }
                    
                    response = self._make_request(
                        "post",
                        "/api/v1/detected_links/check-exists",
                        params=params,
                        timeout=30
                    )
                    
                    if response.status_code != 200:
                        return f"API error {response.status_code}: {response.text}"
                    
                    # Response format: {"{uuid}": true/false}
                    data = response.json()
                    
                    if not isinstance(data, dict):
                        return f"Unexpected response format: {data}"
                    
                    found_any = False
                    for detected_link_id, exists in data.items():
                        if exists:
                            found_any = True
                            detected_results[candidate_url] = detected_link_id
                            logger.info(f"Detected link exists for {candidate_url}: {detected_link_id}")
                        else:
                            logger.info(f"Detected link does not exist for URL: {candidate_url}")
                    
                    if not found_any and not data:
                        logger.info(f"No detected_link_id entries for URL: {candidate_url}")
                
                return None
            
            # Vòng 1: URL gốc + www (nếu có)
            error = _check_variant_list(url_variants)
            if error:
                return None, error
            
            # Nếu vòng 1 không tìm được gì, thử lại với biến thể thêm trailing '/'
            if not detected_results and url_variants:
                slash_variants = []
                for u in url_variants:
                    if not u.endswith("/"):
                        slash_variants.append(u + "/")
                # Loại bỏ trùng lặp
                slash_variants = list(dict.fromkeys(slash_variants))
                
                if slash_variants:
                    error = _check_variant_list(slash_variants)
                    if error:
                        return None, error
            
            # Sau khi check tất cả variants:
            if not detected_results:
                # Không URL nào có detected_link_id -> không phải lỗi, chỉ là "không tồn tại"
                return None, None
            
            if len(detected_results) == 1:
                # Chỉ có một URL variant match -> sử dụng luôn
                only_url, only_id = next(iter(detected_results.items()))
                logger.info(f"Using detected_link_id {only_id} for URL: {only_url}")
                return only_id, None
            
            # Nhiều hơn một variant cùng có detected_link_id
            unique_ids = set(detected_results.values())
            if len(unique_ids) == 1:
                # Các variant đều trỏ tới cùng một ID -> an toàn để dùng
                only_id = next(iter(unique_ids))
                logger.info(
                    f"Multiple URL variants map to same detected_link_id {only_id}: "
                    f"{detected_results}"
                )
                return only_id, None
            
            # Thực sự ambiguous: nhiều URL variants, nhiều detected_link_id khác nhau
            error_msg = (
                "Ambiguous detected_link_id for URL variants. "
                f"Candidates: {detected_results}"
            )
            logger.warning(error_msg)
            return None, error_msg
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error checking exists: {e}")
            return None, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error checking exists: {e}")
            return None, f"Unexpected error: {str(e)}"
    
    def get_domain_id(self, domain: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get domain_id by domain string.
        
        Args:
            domain: Bare domain without scheme (e.g. "spindlersptown.com")
        
        Returns:
            Tuple of (domain_id, error_message)
        """
        if not self._ensure_authenticated():
            return None, "Not authenticated"
        
        try:
            params = {
                "domain": domain,
                "page": 1,
                "page_size": 10,
            }
            response = self._make_request("get", "/api/v1/domains/", params=params, timeout=30)
            if response.status_code != 200:
                return None, f"API error {response.status_code}: {response.text}"
            
            data = response.json()
            items = data.get("data", [])
            if not items:
                return None, None
            
            domain_id = items[0].get("id")
            if not domain_id:
                return None, "No id in domain response"
            
            logger.info(f"Got domain_id: {domain_id} for domain: {domain}")
            return domain_id, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting domain_id: {e}")
            return None, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error getting domain_id: {e}")
            return None, f"Unexpected error: {str(e)}"
    
    def list_detected_links(self, sport_id: str, domain_id: str) -> Tuple[List[Dict], Optional[str]]:
        """
        List detected links for a given sport_id and domain_id.
        
        Args:
            sport_id: Sport UUID
            domain_id: Domain UUID
        
        Returns:
            Tuple of (list_of_detected_links, error_message)
        """
        if not self._ensure_authenticated():
            return [], "Not authenticated"
        
        try:
            params = {
                "sport_ids": sport_id,
                "domain_ids": domain_id,
                "has_image": False,
                "page": 1,
                "page_size": 50,
            }
            response = self._make_request("get", "/api/v1/detected_links/", params=params, timeout=30)
            if response.status_code != 200:
                return [], f"API error {response.status_code}: {response.text}"
            
            data = response.json()
            items = data.get("data", [])
            if not isinstance(items, list):
                return [], f"Unexpected response format: {data}"
            
            logger.info(f"Found {len(items)} detected links for sport_id={sport_id}, domain_id={domain_id}")
            return items, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error listing detected links: {e}")
            return [], f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error listing detected links: {e}")
            return [], f"Unexpected error: {str(e)}"
    
    def upload_image(self, image_path: str, detected_link_id: str, url: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Upload image with detected_link_id
        
        IMPORTANT: This uploads the ORIGINAL FULL image, not a cropped version.
        The cropped image (if USE_CROP=true) is only used for URL extraction and is deleted afterward.
        
        Args:
            image_path: Path to the ORIGINAL FULL image file
            detected_link_id: Detected link ID (UUID string)
            url: Original URL extracted from image (optional, used to derive domain for filename)
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Determine content type from file extension
            import os
            from urllib.parse import urlparse
            import re
            import uuid
            file_ext = os.path.splitext(image_path)[1].lower()
            content_type_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".bmp": "image/bmp"
            }
            content_type = content_type_map.get(file_ext, "image/png")

            # Build upload filename:
            # - Default: original basename
            # - If URL is provided: "<detected_link_id>_<random_uuid>_<domain><ext>"
            #   → random_uuid đảm bảo duy nhất ngay cả khi cùng detected_link_id + domain
            original_basename = os.path.basename(image_path)
            upload_filename = original_basename

            if url:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc or ""
                    random_suffix = uuid.uuid4().hex  # 32-char hex, đủ để tránh trùng
                    if domain:
                        # Sanitize domain for filesystem safety
                        safe_domain = re.sub(r"[^a-zA-Z0-9.-]", "_", domain)
                        upload_filename = f"{detected_link_id}_{random_suffix}_{safe_domain}{file_ext}"
                    else:
                        upload_filename = f"{detected_link_id}_{random_suffix}{file_ext}"
                except Exception as e:
                    logger.warning(f"Failed to parse domain from URL '{url}': {e}")
            
            # Open and upload the ORIGINAL FULL image file
            with open(image_path, "rb") as f:
                files = {
                    "file": (upload_filename, f, content_type)
                }
                data = {
                    "detected_link_id": detected_link_id,
                    "provider": "GOOGLE_CLOUD",
                    "bulk": True  # upload theo dạng bulk, đúng với spec backend
                }
                
                # Remove Content-Type header for multipart/form-data
                upload_headers = {k: v for k, v in self.headers.items() if k != "Content-Type"}
                
                # Use _make_request but override headers for multipart
                if not self._ensure_authenticated():
                    return False, "Not authenticated"
                
                url = f"{self.base_url}/api/v1/detected_link_images/upload"
                response = requests.post(
                    url,
                    files=files,
                    data=data,
                    headers=upload_headers,
                    timeout=60
                )
                
                # Handle 401
                if response.status_code == 401:
                    logger.warning("Got 401, attempting to re-login...")
                    if self.username and self.password:
                        success, error = self.login()
                        if success:
                            upload_headers = {k: v for k, v in self.headers.items() if k != "Content-Type"}
                            with open(image_path, "rb") as f2:
                                files = {
                                    "file": (upload_filename, f2, content_type)
                                }
                                response = requests.post(
                                    url,
                                    files=files,
                                    data=data,
                                    headers=upload_headers,
                                    timeout=60
                                )
            
            if response.status_code == 201:  # Created
                # Log only once (detailed log is in UploadImageTool)
                logger.debug(f"Uploaded image successfully: {image_path}")
                return True, None
            elif response.status_code == 202:  # Accepted (async command queued)
                command_id = None
                correlation_id = None
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        command_id = response_data.get("command_id")
                        correlation_id = response_data.get("correlation_id")
                except ValueError:
                    # Keep backward-compatible success behavior even if payload is not JSON.
                    pass

                logger.info(
                    "Image upload accepted for async processing: "
                    f"image={image_path}, detected_link_id={detected_link_id}, "
                    f"command_id={command_id}, correlation_id={correlation_id}"
                )
                return True, None
            elif response.status_code == 409:  # Conflict - already uploaded
                logger.info(f"Image already uploaded (409): {image_path}")
                return True, None  # Treat as success if already uploaded
            else:
                return False, f"Upload failed {response.status_code}: {response.text}"
                
        except FileNotFoundError:
            return False, f"Image file not found: {image_path}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error uploading image: {e}")
            return False, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error uploading image: {e}")
            return False, f"Unexpected error: {str(e)}"
    
    # Backward compatibility methods
    def detect_link(self, url: str, sport_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Alias for check_exists (backward compatibility)
        
        Args:
            url: URL extracted from image
            sport_id: Sport ID (UUID string)
        
        Returns:
            Tuple of (detected_link_id, error_message)
        """
        return self.check_exists(url, sport_id)
