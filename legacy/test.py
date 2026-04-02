import cv2
import base64
import os
from openai import AzureOpenAI
from PIL import Image

# ============================================
# CẤU HÌNH AZURE OPENAI VISION
# ============================================
# Bước 1: Vào Azure Portal → Azure OpenAI resource
# Bước 2: Vào "Keys and Endpoint" → Copy Key 1 hoặc Key 2
# Bước 3: Copy Endpoint URL (ví dụ: https://my-resource.openai.azure.com)
# Bước 4: Vào "Deployments" → Xem tên deployment (ví dụ: gpt-4-vision)
# Bước 5: Thay các giá trị bên dưới

client = AzureOpenAI(
    api_key="YOUR_AZURE_OPENAI_KEY",  # ← Dán Key 1 hoặc Key 2 vào đây
    api_version="2024-02-15-preview",  # Hoặc version mới nhất
    azure_endpoint="https://YOUR_RESOURCE_NAME.openai.azure.com"  # ← Dán Endpoint vào đây
)

DEPLOYMENT_NAME = "gpt-4-vision"  # ← Tên deployment của bạn

# ============================================
# HÀM ENCODE ẢNH THÀNH BASE64
# ============================================
def encode_image(image_path):
    """Chuyển ảnh thành base64 để gửi đến API"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# ============================================
# EXTRACT URL TỪ THANH ĐỊA CHỈ
# ============================================
print("Đang extract URL bằng Azure OpenAI Vision (GPT-4 Vision)...")
print("=" * 60)

# Tùy chọn: Cắt phần trên cùng để tập trung vào thanh địa chỉ (tùy chọn)
# Có thể bỏ qua bước này và dùng toàn bộ ảnh
USE_CROP = True  # Đặt False nếu muốn dùng toàn bộ ảnh

if USE_CROP:
    # Đọc ảnh và cắt phần trên cùng (thanh địa chỉ trình duyệt)
    img = cv2.imread("image.png")
    height, width = img.shape[:2]
    
    # Cắt 12-15% phần trên của ảnh để tập trung vào thanh địa chỉ
    crop_height = int(height * 0.13)
    address_bar_region = img[0:crop_height, 0:width]
    
    # Lưu phần đã cắt vào file tạm
    temp_file_path = "temp_address_bar.png"
    cv2.imwrite(temp_file_path, address_bar_region)
    image_path = temp_file_path
    print(f"Đã cắt phần trên cùng ({crop_height}px) để tập trung vào thanh địa chỉ")
else:
    image_path = "image.png"
    print("Sử dụng toàn bộ ảnh")

# Encode ảnh
base64_image = encode_image(image_path)

# Gọi Azure OpenAI Vision API với prompt tối ưu
try:
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
                            "Chỉ trả về URL duy nhất, không có text nào khác, không có giải thích. "
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
        temperature=0.1  # Thấp để kết quả nhất quán và chính xác hơn
    )
    
    # Lấy kết quả
    url = response.choices[0].message.content.strip()
    
    # Làm sạch URL - loại bỏ các ký tự không cần thiết
    url = url.replace("```", "").replace("URL:", "").replace("url:", "").strip()
    url = url.replace("\n", "").replace("\r", "")
    
    # Đảm bảo URL có protocol
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    # Xóa file tạm nếu có
    if USE_CROP:
        try:
            os.remove(temp_file_path)
        except:
            pass
    
    if url:
        print("=" * 60)
        print(f"✅ URL tìm thấy: {url}")
        print("=" * 60)
    else:
        print("=" * 60)
        print("❌ Không tìm thấy URL")
        print("=" * 60)
        
except Exception as e:
    print("=" * 60)
    print(f"❌ Lỗi: {e}")
    print("=" * 60)
    print("\n🔍 Kiểm tra lại:")
    print("1. API key đã đúng chưa?")
    print("2. Endpoint đã đúng chưa?")
    print("3. Deployment name đã đúng chưa?")
    print("4. Đã enable GPT-4 Vision trong Azure chưa?")
    print("5. Đã deploy model GPT-4 Vision chưa?")