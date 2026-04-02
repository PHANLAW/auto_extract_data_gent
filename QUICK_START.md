# Quick Start Guide - Chạy Server và Test Workflow

## 🚀 Bước 1: Setup Environment

### 1.1. Install Dependencies

```bash
# Activate virtual environment
.venv\Scripts\activate

# Install packages (nếu chưa install)
pip install -r requirements.txt
```

### 1.2. Configure `.env` file

Copy `.env.example` sang `.env` và điền thông tin:

```bash
copy .env.example .env
```

**Bắt buộc phải config:**
```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini

# Sport API
SPORT_API_BASE_URL=http://localhost:8000
SPORT_API_USERNAME=your-username
SPORT_API_PASSWORD=your-password

# Azure Blob Storage (nếu dùng)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_BLOB_CONTAINER_NAME=image-folders
```

## 🖥️ Bước 2: Chạy Server

### Option 1: Chạy với uvicorn (Recommended)

```bash
# Activate venv
.venv\Scripts\activate

# Chạy server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy tại: `http://localhost:8000`

### Option 2: Chạy với Python

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Chạy background (Windows PowerShell)

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .venv\Scripts\activate; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
```

## 📁 Bước 3: Chuẩn bị Dữ Liệu Test

### 3.1. Tạo folder test trong `data/`

```bash
# Tạo folder với tên đúng format
mkdir "data\02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"

# Copy ảnh vào folder
copy your-image.png "data\02.01.26 00-30 PL 25_26 Crystal Palace - Fulham\image.png"
```

**Format tên folder:**
```
dd.mm.yy hh-mm LEAGUE match_name
```

Ví dụ:
- `02.01.26 00-30 PL 25_26 Crystal Palace - Fulham`
- `15.12.25 14-30 EPL 24_25 Manchester United - Liverpool`

### 3.2. Cấu trúc folder:

```
data/
├── 02.01.26 00-30 PL 25_26 Crystal Palace - Fulham/
│   ├── image1.png
│   ├── image2.png
│   └── ...
```

## 🧪 Bước 4: Test Workflow

### Option A: Test Local Folder (Không cần upload)

```bash
# Test workflow từ folder local
python test_workflow_simple.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

**Kết quả sẽ hiển thị:**
- Parse folder name
- Get league_id và sport_id
- Extract URL từ từng ảnh
- Check detected_link exists
- Summary

### Option B: Test qua API (Server phải đang chạy)

#### 4.1. Test Parse Folder

```bash
curl -X POST "http://localhost:8000/api/v1/parse-folder" ^
  -H "Content-Type: application/json" ^
  -d "{\"folder_name\": \"02.01.26 00-30 PL 25_26 Crystal Palace - Fulham\"}"
```

#### 4.2. Test Process Folder

```bash
curl -X POST "http://localhost:8000/api/v1/process-folder" ^
  -H "Content-Type: application/json" ^
  -d "{\"folder_path\": \"data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham\"}"
```

#### 4.3. Test Upload và Process (Blob Storage)

```bash
# Upload folder và trigger processing
python upload_and_trigger.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

## 📊 Bước 5: Xem Kết Quả

### 5.1. Xem qua API Response

API sẽ trả về JSON với kết quả chi tiết:

```json
{
  "folder": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
  "success": true,
  "match_name": "Crystal Palace - Fulham",
  "league": "PL 25_26",
  "start_time": "2026-01-02 00:30",
  "sport_id": "118e13d8-f4fa-4876-ac32-a9db4a51a0ef",
  "images_processed": 2,
  "images_success": 2,
  "images_failed": 0,
  "image_results": [
    {
      "image": "image.png",
      "success": true,
      "url": "https://b5.thapcam73.life/truc-tiep/...",
      "detected_link_id": "60cf131e-61af-495d-8013-a2981e72e9df"
    }
  ]
}
```

### 5.2. Xem Logs

```bash
# Xem log file
type logs\app.log

# Hoặc tail (nếu có)
Get-Content logs\app.log -Tail 50 -Wait
```

### 5.3. Xem Retry File (nếu có lỗi)

```bash
# Xem file retry
type retry_failed.json
```

### 5.4. Xem API Docs

Mở browser: `http://localhost:8000/docs`

Có thể test trực tiếp các endpoints từ Swagger UI.

## 🔄 Workflow Hoàn Chỉnh

### Scenario 1: Test Local (Không cần Blob Storage)

```bash
# 1. Chạy server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Terminal khác: Test workflow
python test_workflow_simple.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

### Scenario 2: Upload và Process (Với Blob Storage)

```bash
# 1. Chạy server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Terminal khác: Upload và trigger
python upload_and_trigger.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

### Scenario 3: Auto Processing (Background)

```bash
# 1. Config .env
AUTO_PROCESS_ENABLED=true
AUTO_PROCESS_INTERVAL=300
DATA_SOURCE_MODE=blob_storage

# 2. Chạy server (sẽ tự động check mỗi 5 phút)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Upload folder (không cần trigger)
python upload_and_trigger.py "data/folder" --upload-only

# Server sẽ tự động detect và process sau 5 phút
```

## 📋 Checklist

- [ ] Install dependencies
- [ ] Config `.env` file
- [ ] Chạy server
- [ ] Tạo folder test trong `data/`
- [ ] Copy ảnh vào folder
- [ ] Test workflow
- [ ] Xem kết quả

## 🐛 Troubleshooting

### Server không chạy được:

```bash
# Check port đã được dùng chưa
netstat -ano | findstr :8000

# Hoặc đổi port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Lỗi import:

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Lỗi authentication:

- Check `SPORT_API_USERNAME` và `SPORT_API_PASSWORD` trong `.env`
- Check `SPORT_API_BASE_URL` có đúng không

### Lỗi Azure OpenAI:

- Check `AZURE_OPENAI_API_KEY` và `AZURE_OPENAI_ENDPOINT`
- Check deployment name có đúng không

## 📚 Tài Liệu Tham Khảo

- API Docs: `http://localhost:8000/docs`
- Test Scripts: `test_workflow_simple.py`, `upload_and_trigger.py`
- Config: `.env.example`
