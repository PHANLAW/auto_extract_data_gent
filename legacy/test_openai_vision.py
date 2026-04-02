"""
Azure OpenAI Vision (GPT-4 Vision) - Extract URL từ thanh địa chỉ trình duyệt
So sánh với Azure Computer Vision: Đắt hơn nhưng chính xác hơn
"""

import base64
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
def extract_url_with_openai_vision(image_path):
    """Sử dụng Azure OpenAI Vision để extract URL"""
    
    # Encode ảnh
    base64_image = encode_image(image_path)
    
    # Gọi API với prompt cụ thể
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
                            "Chỉ trả về URL duy nhất, không có text nào khác. "
                            "Nếu URL không có http:// hoặc https://, hãy thêm https:// vào đầu. "
                            "Nếu URL bị cắt, hãy trả về phần URL có thể nhìn thấy được."
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
        temperature=0.1  # Thấp để kết quả nhất quán hơn
    )
    
    # Lấy kết quả
    url = response.choices[0].message.content.strip()
    
    # Làm sạch URL
    url = url.replace("```", "").replace("URL:", "").replace("url:", "").strip()
    
    # Đảm bảo URL có protocol
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    return url

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    image_path = "image.png"
    
    print("Đang extract URL bằng Azure OpenAI Vision...")
    print("=" * 50)
    
    try:
        url = extract_url_with_openai_vision(image_path)
        
        if url:
            print(f"✅ URL tìm thấy: {url}")
        else:
            print("❌ Không tìm thấy URL")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        print("\nKiểm tra lại:")
        print("1. API key đã đúng chưa?")
        print("2. Endpoint đã đúng chưa?")
        print("3. Deployment name đã đúng chưa?")
        print("4. Đã enable GPT-4 Vision trong Azure chưa?")
