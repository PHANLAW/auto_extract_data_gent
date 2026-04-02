# Workflow Guide - Hướng Dẫn Chạy Toàn Bộ Workflow

## 🎯 Mục Đích

Hướng dẫn chi tiết cách chạy server và test toàn bộ workflow từ đầu đến cuối.

## 📋 Quy Trình

### Bước 1: Chuẩn Bị

#### 1.1. Config `.env`

```bash
# Copy .env.example
copy .env.example .env

# Edit .env và điền:
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_ENDPOINT  
# - SPORT_API_BASE_URL
# - SPORT_API_USERNAME
# - SPORT_API_PASSWORD
```

#### 1.2. Chuẩn Bị Dữ Liệu

Tạo folder trong `data/` với format đúng:

```bash
mkdir "data\02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
copy your-image.png "data\02.01.26 00-30 PL 25_26 Crystal Palace - Fulham\image.png"
```

### Bước 2: Chạy Server

#### Option 1: Dùng Script (Windows)

```bash
start_server.bat
```

#### Option 2: Manual

```bash
# Activate venv
.venv\Scripts\activate

# Chạy server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy tại: `http://localhost:8000`

**Kiểm tra server:**
- Mở browser: `http://localhost:8000/docs` (Swagger UI)
- Hoặc: `http://localhost:8000/` (Health check)

### Bước 3: Test Workflow

#### Option A: Dùng Demo Script (Recommended)

```bash
# Terminal mới (server đang chạy ở terminal khác)
python demo_full_workflow.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

Script sẽ:
- Check server đang chạy
- Gọi API process folder
- Hiển thị kết quả chi tiết

#### Option B: Dùng Test Script (Local, không cần server)

```bash
python test_workflow_simple.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

#### Option C: Dùng API trực tiếp

```bash
# Process folder
curl -X POST "http://localhost:8000/api/v1/process-folder" ^
  -H "Content-Type: application/json" ^
  -d "{\"folder_path\": \"data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham\"}"
```

### Bước 4: Xem Kết Quả

#### 4.1. Từ API Response

Response JSON sẽ có:
```json
{
  "folder": "...",
  "success": true,
  "match_name": "...",
  "league": "...",
  "sport_id": "...",
  "images_processed": 2,
  "images_success": 2,
  "image_results": [
    {
      "image": "image.png",
      "success": true,
      "url": "https://...",
      "detected_link_id": "..."
    }
  ]
}
```

#### 4.2. Từ Logs

```bash
# Xem log file
type logs\app.log

# Hoặc tail
Get-Content logs\app.log -Tail 50 -Wait
```

#### 4.3. Từ Swagger UI

Mở `http://localhost:8000/docs` và test các endpoints trực tiếp.

#### 4.4. Retry File (nếu có lỗi)

```bash
type retry_failed.json
```

## 🔄 Workflow Chi Tiết

### 1. Parse Folder Name
```
Input: "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
Output:
  - start_time: "2026-01-02 00:30"
  - league: "PL 25_26"
  - match_name: "Crystal Palace - Fulham"
```

### 2. Get League ID
```
API: GET /api/v1/leagues/?name=PL 25_26
Response: {"data": [{"id": "..."}], ...}
Lấy: data[0].id
```

### 3. Get Sport ID
```
API: GET /api/v1/sports/?league_id=...&match_name=...&start_time=...
Response: {"data": [{"id": "..."}], ...}
Lấy: data[0].id
```

### 4. Process Images
```
For each image:
  a. Extract URL (Azure OpenAI Vision)
  b. Check exists: POST /api/v1/detected_links/check-exists?url=...&sport_id=...
  c. If exists: Upload image: POST /api/v1/detected_link_images/upload
  d. If not exists: Write to retry_failed.json
```

## 📊 Example Output

```
================================================================================
DEMO: Full Workflow Test
================================================================================

[STEP 1] Checking server...
[SUCCESS] Server đang chạy tại http://localhost:8000

[STEP 2] Checking folder...
[SUCCESS] Folder: 02.01.26 00-30 PL 25_26 Crystal Palace - Fulham
[INFO] Tìm thấy 1 ảnh

[STEP 3] Processing folder...
--------------------------------------------------------------------------------
Calling API: POST http://localhost:8000/api/v1/process-folder
Payload: {'folder_path': 'data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham'}

[SUCCESS] Processing completed!

================================================================================
RESULTS
================================================================================
Folder: 02.01.26 00-30 PL 25_26 Crystal Palace - Fulham
Success: True

Match Info:
  Match Name: Crystal Palace - Fulham
  League: PL 25_26
  Start Time: 2026-01-02 00:30
  Sport ID: 118e13d8-f4fa-4876-ac32-a9db4a51a0ef

Images:
  Processed: 1
  Success: 1
  Failed: 0

Details:
  [SUCCESS] image.png
    URL: https://b5.thapcam73.life/truc-tiep/crystal-palace-vs-fulham-3Uau1i0
    Detected Link ID: 60cf131e-61af-495d-8013-a2981e72e9df
```

## 🚀 Quick Commands

```bash
# 1. Start server
start_server.bat

# 2. Test workflow (terminal khác)
python demo_full_workflow.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"

# 3. Xem logs
type logs\app.log

# 4. Xem API docs
# Mở browser: http://localhost:8000/docs
```

## ⚠️ Troubleshooting

### Server không start:
- Check port 8000 đã được dùng chưa
- Check `.env` file có đúng không
- Check dependencies đã install chưa

### API error:
- Check server đang chạy
- Check credentials trong `.env`
- Check network connection

### Processing failed:
- Check folder name format
- Check ảnh có hợp lệ không
- Check logs để xem chi tiết lỗi
