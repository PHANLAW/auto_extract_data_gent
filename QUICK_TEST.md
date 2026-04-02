# Quick Test - Test URL Extraction

## 🚀 Cách Test Nhanh

### 1. Test một ảnh đơn

```bash
# Activate venv
.venv\Scripts\activate

# Test ảnh
python test_url_extraction.py image.png
```

### 2. Test với expected URL để verify

```bash
python test_url_extraction.py image.png "https://expected-url.com"
```

### 3. Test tất cả ảnh trong folder

```bash
# Test folder data/
python test_url_extraction.py data/

# Test folder cụ thể
python test_url_extraction.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

### 4. Test độ chính xác với expected results

#### Bước 1: Tạo template
```bash
python test_accuracy_batch.py data/
```

#### Bước 2: Điền expected URLs vào `expected_urls.json`

#### Bước 3: Chạy accuracy test
```bash
python test_accuracy_batch.py data/ expected_urls.json
```

## 📊 Kết Quả

- Kết quả sẽ hiển thị trên console
- File JSON chi tiết sẽ được lưu:
  - `test_results_YYYYMMDD_HHMMSS.json` - Kết quả test
  - `accuracy_results_YYYYMMDD_HHMMSS.json` - Kết quả accuracy

## 🔍 Xem Prompt

Prompt được lưu trong: `prompts/url_extraction.yaml`

Sau khi chỉnh prompt, reload:
```python
from app.core.prompt_loader import prompt_loader
prompt_loader.reload_prompt("url_extraction")
```

## ⚠️ Lưu Ý

1. Đảm bảo đã config `.env` với Azure OpenAI credentials
2. Ảnh phải có định dạng: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`
3. Nếu có lỗi connection, kiểm tra Azure OpenAI endpoint và API key
