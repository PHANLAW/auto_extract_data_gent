"""
Batch Processing: Extract URL từ 8,700 ảnh với độ chính xác cao
- Sử dụng Azure OpenAI Vision (GPT-4o hoặc gpt-4o-mini)
- Tích hợp API hệ thống để check và upload
- Lưu kết quả để review nếu không match 100%
"""

import cv2
import base64
import os
import json
import time
import re
from datetime import datetime
from pathlib import Path
from openai import AzureOpenAI
import requests
from typing import Dict, Optional, Tuple

# ============================================
# CẤU HÌNH AZURE OPENAI VISION
# ============================================
client = AzureOpenAI(
    api_key="YOUR_AZURE_OPENAI_KEY",  # ← Thay bằng API key của bạn
    api_version="2024-02-15-preview",
    azure_endpoint="https://YOUR_RESOURCE_NAME.openai.azure.com"  # ← Thay bằng endpoint
)

DEPLOYMENT_NAME = "gpt-4o-mini"  # ← Dùng gpt-4o-mini để tiết kiệm, hoặc "gpt-4o" để chính xác hơn

# ============================================
# CẤU HÌNH API HỆ THỐNG
# ============================================
SYSTEM_API_BASE_URL = "https://your-system-api.com"  # ← Thay bằng URL API hệ thống của bạn
SYSTEM_API_KEY = "YOUR_SYSTEM_API_KEY"  # ← Thay bằng API key hệ thống

# ============================================
# CẤU HÌNH XỬ LÝ
# ============================================
IMAGES_FOLDER = "images"  # Thư mục chứa 8,700 ảnh
RESULTS_FILE = "results.json"  # File lưu kết quả
REVIEW_FILE = "needs_review.json"  # File lưu các ảnh cần review
LOG_FILE = "processing_log.txt"  # File log

# Cấu hình crop ảnh
USE_CROP = True  # Cắt phần trên để tập trung vào thanh địa chỉ
CROP_RATIO = 0.13  # 13% phần trên của ảnh

# Rate limiting để tránh quá tải API
DELAY_BETWEEN_REQUESTS = 0.5  # Giây giữa các request (điều chỉnh nếu cần)

# ============================================
# HÀM TIỆN ÍCH
# ============================================
def log(message: str, level: str = "INFO"):
    """Ghi log vào file và console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

def encode_image(image_path: str) -> str:
    """Chuyển ảnh thành base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def validate_url(url: str) -> bool:
    """Kiểm tra URL có hợp lệ không"""
    if not url:
        return False
    # Pattern cơ bản để validate URL
    url_pattern = re.compile(
        r'^https?://'  # http:// hoặc https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))

def normalize_url(url: str) -> str:
    """Chuẩn hóa URL"""
    if not url:
        return ""
    
    # Loại bỏ các ký tự không cần thiết
    url = url.replace("```", "").replace("URL:", "").replace("url:", "").strip()
    url = url.replace("\n", "").replace("\r", "").replace(" ", "")
    
    # Đảm bảo có protocol
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    return url

# ============================================
# EXTRACT URL TỪ ẢNH
# ============================================
def extract_url_from_image(image_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract URL từ ảnh sử dụng Azure OpenAI Vision
    Returns: (url, error_message)
    """
    try:
        # Cắt ảnh nếu cần
        if USE_CROP:
            img = cv2.imread(image_path)
            if img is None:
                return None, "Không thể đọc ảnh"
            
            height, width = img.shape[:2]
            crop_height = int(height * CROP_RATIO)
            address_bar_region = img[0:crop_height, 0:width]
            
            temp_file = "temp_crop.png"
            cv2.imwrite(temp_file, address_bar_region)
            image_to_process = temp_file
        else:
            image_to_process = image_path
        
        # Encode ảnh
        base64_image = encode_image(image_to_process)
        
        # Xóa file tạm
        if USE_CROP:
            try:
                os.remove(temp_file)
            except:
                pass
        
        # Gọi Azure OpenAI Vision API
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Trong ảnh này có một trình duyệt web. "
                                "Hãy tìm và trích xuất URL từ thanh địa chỉ (address bar) ở trên cùng của trình duyệt. "
                                "Chỉ trả về URL duy nhất, không có text nào khác, không có giải thích, không có dấu ngoặc kép. "
                                "Nếu URL không có http:// hoặc https://, hãy thêm https:// vào đầu. "
                                "Nếu URL bị cắt một phần, hãy trả về phần URL có thể nhìn thấy được trong ảnh."
                            )
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
            max_tokens=300,
            temperature=0.1  # Thấp để kết quả nhất quán và chính xác
        )
        
        # Lấy kết quả
        url = response.choices[0].message.content.strip()
        url = normalize_url(url)
        
        # Validate URL
        if not validate_url(url):
            return None, f"URL không hợp lệ: {url}"
        
        return url, None
        
    except Exception as e:
        return None, f"Lỗi khi extract URL: {str(e)}"

# ============================================
# TÍCH HỢP API HỆ THỐNG
# ============================================
def check_url_exists(url: str) -> Tuple[bool, Optional[str]]:
    """
    Gọi API hệ thống để check URL đã tồn tại chưa
    Returns: (exists, error_message)
    """
    try:
        # Thay đổi endpoint này theo API hệ thống của bạn
        response = requests.get(
            f"{SYSTEM_API_BASE_URL}/api/check-url",
            params={"url": url},
            headers={"Authorization": f"Bearer {SYSTEM_API_KEY}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # Điều chỉnh logic này theo response của API hệ thống bạn
            exists = data.get("exists", False)
            return exists, None
        else:
            return False, f"API error: {response.status_code}"
            
    except Exception as e:
        return False, f"Lỗi khi gọi API: {str(e)}"

def upload_image(image_path: str, url: str) -> Tuple[bool, Optional[str]]:
    """
    Upload ảnh lên hệ thống
    Returns: (success, error_message)
    """
    try:
        with open(image_path, "rb") as f:
            files = {"image": f}
            data = {"url": url}
            
            response = requests.post(
                f"{SYSTEM_API_BASE_URL}/api/upload",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {SYSTEM_API_KEY}"},
                timeout=30
            )
        
        if response.status_code == 200:
            return True, None
        else:
            return False, f"Upload failed: {response.status_code}"
            
    except Exception as e:
        return False, f"Lỗi khi upload: {str(e)}"

# ============================================
# XỬ LÝ BATCH
# ============================================
def process_batch():
    """Xử lý tất cả ảnh trong thư mục"""
    
    # Load kết quả đã xử lý (nếu có)
    processed_images = set()
    results = []
    needs_review = []
    
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            existing_results = json.load(f)
            processed_images = {r["image"] for r in existing_results}
            results = existing_results
        log(f"Đã load {len(processed_images)} ảnh đã xử lý")
    
    # Lấy danh sách ảnh
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    image_files = [
        f for f in os.listdir(IMAGES_FOLDER)
        if Path(f).suffix.lower() in image_extensions
    ]
    
    total_images = len(image_files)
    log(f"Tổng số ảnh cần xử lý: {total_images}")
    
    processed_count = 0
    success_count = 0
    review_count = 0
    error_count = 0
    
    for idx, image_file in enumerate(image_files, 1):
        image_path = os.path.join(IMAGES_FOLDER, image_file)
        
        # Bỏ qua nếu đã xử lý
        if image_file in processed_images:
            log(f"[{idx}/{total_images}] Đã xử lý: {image_file}")
            continue
        
        log(f"[{idx}/{total_images}] Đang xử lý: {image_file}")
        
        # Extract URL
        url, error = extract_url_from_image(image_path)
        
        if error:
            log(f"  ❌ Lỗi extract URL: {error}", "ERROR")
            error_count += 1
            results.append({
                "image": image_file,
                "url": None,
                "status": "error",
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue
        
        if not url:
            log(f"  ⚠️  Không tìm thấy URL", "WARNING")
            review_count += 1
            needs_review.append({
                "image": image_file,
                "url": None,
                "reason": "Không tìm thấy URL",
                "timestamp": datetime.now().isoformat()
            })
            results.append({
                "image": image_file,
                "url": None,
                "status": "no_url",
                "timestamp": datetime.now().isoformat()
            })
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue
        
        log(f"  ✅ URL tìm thấy: {url}")
        
        # Check URL trong hệ thống
        exists, check_error = check_url_exists(url)
        
        if check_error:
            log(f"  ⚠️  Lỗi khi check URL: {check_error}", "WARNING")
            review_count += 1
            needs_review.append({
                "image": image_file,
                "url": url,
                "reason": f"Lỗi check URL: {check_error}",
                "timestamp": datetime.now().isoformat()
            })
            results.append({
                "image": image_file,
                "url": url,
                "status": "check_error",
                "error": check_error,
                "timestamp": datetime.now().isoformat()
            })
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue
        
        if exists:
            # URL đã tồn tại → Upload ảnh
            log(f"  📤 URL đã tồn tại, đang upload ảnh...")
            upload_success, upload_error = upload_image(image_path, url)
            
            if upload_success:
                log(f"  ✅ Upload thành công!", "SUCCESS")
                success_count += 1
                results.append({
                    "image": image_file,
                    "url": url,
                    "status": "uploaded",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                log(f"  ❌ Upload thất bại: {upload_error}", "ERROR")
                review_count += 1
                needs_review.append({
                    "image": image_file,
                    "url": url,
                    "reason": f"Upload failed: {upload_error}",
                    "timestamp": datetime.now().isoformat()
                })
                results.append({
                    "image": image_file,
                    "url": url,
                    "status": "upload_failed",
                    "error": upload_error,
                    "timestamp": datetime.now().isoformat()
                })
        else:
            # URL không tồn tại → Cần review
            log(f"  ⚠️  URL không tồn tại trong hệ thống (match < 100%)", "WARNING")
            review_count += 1
            needs_review.append({
                "image": image_file,
                "url": url,
                "reason": "URL không tồn tại trong hệ thống",
                "timestamp": datetime.now().isoformat()
            })
            results.append({
                "image": image_file,
                "url": url,
                "status": "needs_review",
                "timestamp": datetime.now().isoformat()
            })
        
        processed_count += 1
        
        # Lưu kết quả định kỳ (mỗi 10 ảnh)
        if processed_count % 10 == 0:
            save_results(results, needs_review)
            log(f"  💾 Đã lưu kết quả tạm thời ({processed_count} ảnh)")
        
        # Delay giữa các request
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Lưu kết quả cuối cùng
    save_results(results, needs_review)
    
    # Tóm tắt
    log("=" * 60)
    log("TÓM TẮT KẾT QUẢ")
    log("=" * 60)
    log(f"Tổng số ảnh: {total_images}")
    log(f"Đã xử lý: {processed_count}")
    log(f"Upload thành công: {success_count}")
    log(f"Cần review: {review_count}")
    log(f"Lỗi: {error_count}")
    log("=" * 60)

def save_results(results: list, needs_review: list):
    """Lưu kết quả vào file"""
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(needs_review, f, ensure_ascii=False, indent=2)

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    log("=" * 60)
    log("BẮT ĐẦU BATCH PROCESSING")
    log("=" * 60)
    log(f"Model: {DEPLOYMENT_NAME}")
    log(f"Thư mục ảnh: {IMAGES_FOLDER}")
    log(f"Use crop: {USE_CROP}")
    log("=" * 60)
    
    try:
        process_batch()
        log("Hoàn thành!")
    except KeyboardInterrupt:
        log("Đã dừng bởi người dùng", "WARNING")
    except Exception as e:
        log(f"Lỗi nghiêm trọng: {str(e)}", "ERROR")
        raise
