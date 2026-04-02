# API Design - Orchestrator & Auto Handler

## Tổng quan

Server này là **orchestrator và auto handler**, không phải Sport API. Tất cả các API của Sport API được gọi **bên trong** hệ thống, không expose ra ngoài.

## Cấu trúc API

### 1. Health Check

**`GET /api/v1/health`**

Kiểm tra trạng thái server.

---

## 2. Nhóm Processing APIs - Điều khiển Workflow

Base path: `/api/v1/processing`

### 2.1. Bật/tắt Auto Processing (Blob Storage)

**`POST /api/v1/processing/blob-auto`**

Bật hoặc tắt auto-processing cho blob storage.

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "enabled": true,
  "error": null
}
```

**Lưu ý:**
- Chỉ hoạt động khi `DATA_SOURCE_MODE=blob_storage`
- Nếu `DATA_SOURCE_MODE=local`, sẽ trả về lỗi

---

### 2.2. Kiểm tra Folder Cần Xử Lý

**`GET /api/v1/processing/pending-folders`**

Kiểm tra xem có folder nào cần xử lý không.

**Response (local mode):**
```json
{
  "mode": "local",
  "source": "data",
  "folders": [
    {
      "name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
      "status": "new"
    },
    {
      "name": "15.12.25 14-30 EPL 24_25 Manchester United - Liverpool",
      "status": "processed"
    }
  ]
}
```

**Response (blob_storage mode):**
```json
{
  "mode": "blob_storage",
  "source": "image-folders",
  "folders": [
    {
      "name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
      "status": "new"
    }
  ]
}
```

**Logic:**
- **local mode**: Scan `LOCAL_DATA_PATH` (thường là `data/`), so với state để biết folder nào là "new"
- **blob_storage mode**: List folders từ blob storage, so với state để biết folder nào là "new"

---

### 2.3. Bắt Đầu Xử Lý

**`POST /api/v1/processing/start`**

Bắt đầu xử lý các folder mới.

**Request Body:**
```json
{
  "mode": "auto",        // "auto" | "local" | "blob_storage"
  "max_folders": 10      // optional: giới hạn số folder xử lý
}
```

**Response:**
```json
{
  "success": true,
  "mode": "blob_storage",
  "checked": 5,
  "new_folders": 2,
  "processed": 2,
  "results": [
    {
      "folder": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
      "success": true,
      "match_name": "Crystal Palace - Fulham",
      "league": "PL 25_26",
      "start_time": "2026-01-02 00:30",
      "sport_id": "881f9172-7413-4fd0-9765-b529e01a70fd",
      "images_processed": 3,
      "images_success": 3,
      "images_failed": 0,
      "image_results": [...]
    }
  ],
  "error": null
}
```

**Workflow cho mỗi folder:**
1. Parse folder name → `match_name`, `league`, `start_time`
2. Gọi Sport API:
   - `GET /api/v1/leagues/?name={league}` → `league_id`
   - `GET /api/v1/sports/?league_id={id}&match_name={name}&start_time={time}` → `sport_id`
3. Với mỗi image trong folder:
   - Agent extract URL từ image
   - `POST /api/v1/detected_links/check-exists?url={url}&sport_id={id}` → `detected_link_id`
   - Nếu có `detected_link_id`:
     - `POST /api/v1/detected_link_images/upload` với `detected_link_id`, `provider=GOOGLE_CLOUD`, và file
   - Nếu không có `detected_link_id`:
     - Ghi vào `retry_failed.json` với URL, match_name, image_name

**Logic:**
- Nếu `mode="auto"`: Dùng `DATA_SOURCE_MODE` từ `.env`
- Nếu `mode="local"`: Chỉ xử lý folder từ `LOCAL_DATA_PATH`
- Nếu `mode="blob_storage"`: Chỉ xử lý folder từ blob storage

---

## 3. Nhóm Blob Storage APIs - Quản Lý Blob

Base path: `/api/v1/blob`

### 3.1. Upload Folder Lên Blob Storage

**`POST /api/v1/blob/folders/upload`**

Upload một folder local lên Azure Blob Storage.

**Request Body:**
```json
{
  "local_folder_path": "data/02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
  "target_folder_name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"  // optional
}
```

**Response:**
```json
{
  "success": true,
  "folder_name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
  "uploaded_files": 3,
  "error": null
}
```

**Lưu ý:**
- Chỉ upload các file ảnh (theo `IMAGE_EXTENSIONS`)
- Folder name sẽ được normalize để Windows-safe (thay `:` thành `-`)

---

### 3.2. List Folders Trong Blob Storage

**`GET /api/v1/blob/folders`**

List tất cả folders trong blob storage.

**Query Params:**
- `name` (optional): Filter theo tên folder (partial match)

**Response:**
```json
{
  "folders": [
    {
      "name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
      "files": 3
    },
    {
      "name": "15.12.25 14-30 EPL 24_25 Manchester United - Liverpool",
      "files": 5
    }
  ],
  "total": 2
}
```

---

### 3.3. Xóa Folder Trong Blob Storage

**`DELETE /api/v1/blob/folders/{folder_name}`**

Xóa một folder và tất cả files trong folder đó.

**Response:**
```json
{
  "success": true,
  "deleted_files": 3,
  "error": null
}
```

---

### 3.4. Xóa File Trong Blob Storage

**`DELETE /api/v1/blob/files`**

Xóa một file cụ thể trong blob storage.

**Request Body:**
```json
{
  "folder_name": "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham",
  "file_name": "image.png"
}
```

**Response:**
```json
{
  "success": true,
  "error": null
}
```

---

## Cấu Hình DATA_SOURCE_MODE

### Local Mode (`DATA_SOURCE_MODE=local`)

- **Nguồn dữ liệu**: Folder trong `LOCAL_DATA_PATH` (mặc định: `data/`)
- **API hoạt động**:
  - `/processing/pending-folders`: List folders trong `data/` với status
  - `/processing/start`: Xử lý folders từ `data/`
- **API không hoạt động**:
  - `/processing/blob-auto`: Trả về lỗi (chỉ dùng cho blob_storage)

### Blob Storage Mode (`DATA_SOURCE_MODE=blob_storage`)

- **Nguồn dữ liệu**: Azure Blob Storage container
- **API hoạt động**:
  - `/processing/blob-auto`: Bật/tắt auto-processing
  - `/processing/pending-folders`: List folders từ blob với status
  - `/processing/start`: Xử lý folders từ blob
- **Auto-processing**: Nếu bật qua `/processing/blob-auto`, server sẽ tự động check và xử lý folder mới theo interval

---

## Các API Đã Bỏ

Các API sau **không còn xuất hiện** trong Swagger UI:

- ❌ `/api/v1/parse-folder`
- ❌ `/api/v1/get-sport-id`
- ❌ `/api/v1/extract-url`
- ❌ `/api/v1/detect-link`
- ❌ `/api/v1/upload-image`
- ❌ `/api/v1/process-image`
- ❌ `/api/v1/process-folder` (thay bằng `/processing/start`)
- ❌ `/api/v1/upload-folder` (thay bằng `/blob/folders/upload`)
- ❌ `/api/v1/upload-and-process` (thay bằng `/blob/folders/upload` + `/processing/start`)
- ❌ `/api/v1/trigger-blob-check` (thay bằng `/processing/start` với `mode=blob_storage`)

**Lý do**: Server này chỉ là orchestrator, các chức năng nhỏ được gọi **bên trong** workflow, không expose ra ngoài.

---

## Workflow Tổng Quan

### Local Mode Workflow:

1. Đặt folder vào `data/`
2. Gọi `GET /api/v1/processing/pending-folders` để xem folder mới
3. Gọi `POST /api/v1/processing/start` với `mode="local"` để xử lý

### Blob Storage Mode Workflow:

1. Upload folder: `POST /api/v1/blob/folders/upload`
2. (Optional) Bật auto-processing: `POST /api/v1/processing/blob-auto` với `enabled=true`
3. Nếu không dùng auto:
   - Check: `GET /api/v1/processing/pending-folders`
   - Process: `POST /api/v1/processing/start` với `mode="blob_storage"`

---

## State Management

- **Local folders**: Lưu trong `tracker_state.json` với key `local_processed_folders`
- **Blob folders**: Lưu trong `tracker_state.json` với key `processed_folders`
- **Auto-processing state**: Lưu trong `processing_state.json` với key `blob_auto_enabled`
