# Auto Upload và Trigger Processing

## 🎯 Mục Đích

Tự động upload folder lên Azure Blob Storage và trigger server để xử lý folder đó.

## 📋 Workflow

1. **Upload folder** → Azure Blob Storage
2. **Trigger processing** → Server tự động check và xử lý folder mới

## 🚀 Cách Sử Dụng

### 1. Upload và Trigger (All-in-one)

```bash
python upload_and_trigger.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
```

Script sẽ:
- Upload folder lên Azure Blob Storage
- Tự động trigger server check và xử lý folder đó

### 2. Upload Only

```bash
python upload_and_trigger.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham" --upload-only
```

Chỉ upload folder, không trigger processing.

### 3. Trigger Only

```bash
python upload_and_trigger.py --trigger-only
```

Chỉ trigger server check và xử lý folders mới trong blob storage.

### 4. Custom API URL

```bash
python upload_and_trigger.py "data/folder" --api-url http://your-server.com:8000
```

## 📡 API Endpoints

### POST `/api/v1/upload-folder`

Upload folder lên Azure Blob Storage.

**Request:**
```json
{
  "folder_path": "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
}
```

**Response:**
```json
{
  "success": true,
  "folder_name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
  "message": "Folder '...' uploaded successfully"
}
```

### POST `/api/v1/upload-and-process`

Upload folder và trigger processing.

**Request:**
```json
{
  "folder_path": "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
}
```

**Response:**
```json
{
  "success": true,
  "folder_name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
  "uploaded": true,
  "processed": true,
  "processing_result": {
    "folder": "...",
    "success": true,
    "images_processed": 2,
    "images_success": 2,
    "images_failed": 0
  }
}
```

### POST `/api/v1/trigger-blob-check`

Trigger manual check cho folders mới trong blob storage.

**Response:**
```json
{
  "success": true,
  "checked": 5,
  "new_folders": 1,
  "processed": 1,
  "results": [...]
}
```

## ⚙️ Configuration

### `.env` file:

```env
# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_BLOB_CONTAINER_NAME=image-folders
AZURE_BLOB_PREFIX=

# Auto Processing (optional)
AUTO_PROCESS_ENABLED=false
AUTO_PROCESS_INTERVAL=300
```

## 🔄 Workflow Chi Tiết

### Upload và Process:

1. **Upload Folder**:
   - Tìm tất cả ảnh trong folder
   - Upload từng ảnh lên blob storage với path: `{prefix}/{folder_name}/{image_name}`
   - Folder name được normalize (Windows-safe)

2. **Trigger Processing**:
   - Server check folders mới trong blob storage
   - Download folder về local temp directory
   - Parse folder name → `start_time`, `league`, `match_name`
   - Get `league_id` → Get `sport_id`
   - Process từng ảnh:
     - Extract URL từ ảnh
     - Check detected_link exists
     - Upload image nếu detected_link exists
   - Cleanup temp folder
   - Mark folder as processed

## 📝 Example

```bash
# 1. Upload và trigger
python upload_and_trigger.py "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"

# Output:
# [STEP 1] Uploading folder to Azure Blob Storage...
# [SUCCESS] Folder uploaded successfully!
#   Folder name: 02.01.26 00-30 PL 25_26 Crystal Palace - Fulham
#   Uploaded: True
#   Processed: True
# 
# [PROCESSING RESULT]
#   Success: True
#   Images processed: 2
#   Images success: 2
#   Images failed: 0
```

## 🔍 Monitoring

- Check logs: `logs/app.log`
- Check API docs: `http://localhost:8000/docs`
- Check processing status qua API response

## ⚠️ Lưu Ý

1. Đảm bảo Azure Storage Connection String đã config
2. Đảm bảo server đang chạy khi trigger
3. Folder name phải đúng format để parse được
4. Ảnh phải có định dạng hợp lệ
