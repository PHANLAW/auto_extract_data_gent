# AI Agent Workflow for Image Processing

This system processes images from folders containing match information, extracts URLs, and uploads them to an API.

## Workflow Overview

1. **Parse Folder Names**: Extract `match_name`, `league`, and `start_time` from folder names
   - Format: `dd.mm.yy hh:mm LEAGUE match_name`
   - Example: `02.01.26 00:30 PL 25_26 Crystal Palace - Fulham`

2. **Get Sport ID**: Call API with parsed information to get `sport_id`

3. **Process Images**: For each image in the folder:
   - Extract URL from image using Azure OpenAI Vision
   - Call API to detect link and get `detected_link_id`
   - Upload image with `detected_link_id`

4. **Error Handling**: If `detected_link_id` is not found, write to retry file (JSON/CSV)

## File Structure

- `folder_parser.py`: Parses folder names to extract match information
- `sport_api.py`: API client for sport_id, detect_link, and upload operations
- `url_extractor.py`: Extracts URLs from images using Azure OpenAI Vision
- `error_handler.py`: Handles errors by writing to retry files
- `agent.py`: AI agent that orchestrates URL extraction and API calls
- `main_workflow.py`: Main workflow orchestrator

## Configuration

### 1. Azure OpenAI Configuration

Edit `main_workflow.py`:

```python
AZURE_OPENAI_API_KEY = "YOUR_AZURE_OPENAI_KEY"
AZURE_OPENAI_ENDPOINT = "https://YOUR_RESOURCE_NAME.openai.azure.com"
AZURE_OPENAI_DEPLOYMENT = "gpt-4o-mini"  # or "gpt-4o"
```

### 2. Sport API Configuration

Edit `sport_api.py`:

```python
SPORT_API_BASE_URL = "https://your-api.com"
SPORT_API_KEY = "YOUR_API_KEY"  # Optional, if required
```

### 3. Folder Configuration

Edit `main_workflow.py`:

```python
BASE_FOLDER = "."  # Path to folder containing match folders
```

### 4. API Endpoints

Update the API endpoints in `sport_api.py` to match your actual API:

- `get_sport_id()`: Endpoint for getting sport_id
- `detect_link()`: Endpoint for detecting link and getting detected_link_id
- `upload_image()`: Endpoint for uploading image

## Usage

### Basic Usage

```python
from main_workflow import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
results = orchestrator.process_all_folders("./match_folders")
orchestrator.save_results(results)
```

### Run from Command Line

```bash
python main_workflow.py
```

### Process Single Folder

```python
from main_workflow import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
result = orchestrator.process_folder("./02.01.26 00:30 PL 25_26 Crystal Palace - Fulham")
```

## API Response Format

The system expects the following API response formats:

### Get Sport ID Response

```json
{
  "sport_id": 123,
  // or "id": 123,
  // or "sportId": 123
}
```

### Detect Link Response

```json
{
  "detected_link_id": 456,
  // or "link_id": 456,
  // or "id": 456
}
```

### Upload Image Response

- Status code: 200 for success
- Any other status code is treated as failure

## Error Handling

When `detected_link_id` is not found, the system writes to a retry file:

- **JSON format** (`retry_failed.json`):
```json
[
  {
    "match_name": "Crystal Palace - Fulham",
    "image_name": "image1.png",
    "url": "https://b5.thapcam73.life/...",
    "error": "No detected_link_id in response",
    "timestamp": "2026-01-02T00:30:00"
  }
]
```

- **CSV format** (`retry_failed.csv`):
```csv
match_name,image_name,url,error,timestamp
Crystal Palace - Fulham,image1.png,https://b5.thapcam73.life/...,No detected_link_id in response,2026-01-02T00:30:00
```

## Folder Name Format

Folder names should follow this format:
```
dd.mm.yy hh:mm LEAGUE match_name
```

Examples:
- `02.01.26 00:30 PL 25_26 Crystal Palace - Fulham`
- `15.12.25 14:30 EPL 24_25 Manchester United - Liverpool`
- `01.06.26 20:00 La Liga 25_26 Barcelona - Real Madrid`

The parser extracts:
- **start_time**: Converted to `yyyy-mm-dd hh:mm` format (e.g., `2026-01-02 00:30`)
- **league**: League identifier (e.g., `PL 25_26`)
- **match_name**: Match name (e.g., `Crystal Palace - Fulham`)

## Supported Image Formats

- `.png`
- `.jpg`
- `.jpeg`
- `.bmp`
- `.gif`

## Logging

All operations are logged to `workflow_log.txt` with timestamps.

## Results

Processing results are saved to `workflow_results.json` with:
- Summary statistics
- Detailed results for each folder
- Image processing results

## Customization

### Change Retry File Format

Edit `main_workflow.py`:

```python
RETRY_FILE = "retry_failed.csv"
RETRY_FILE_FORMAT = "csv"  # or "json"
```

### Disable Image Cropping

Edit `main_workflow.py`:

```python
USE_CROP = False
```

### Adjust Crop Ratio

Edit `main_workflow.py`:

```python
CROP_RATIO = 0.15  # 15% of image height
```

## Troubleshooting

### Folder Name Parsing Issues

If folder names don't parse correctly, check the format matches:
```
dd.mm.yy hh:mm LEAGUE match_name
```

### API Connection Issues

- Verify `SPORT_API_BASE_URL` is correct
- Check `SPORT_API_KEY` if authentication is required
- Verify API endpoints match your actual API structure

### URL Extraction Issues

- Ensure Azure OpenAI credentials are correct
- Check that the vision model is deployed
- Verify image files are readable

### Missing detected_link_id

If `detected_link_id` is not found:
1. Check API response structure matches expected format
2. Review `retry_failed.json` or `retry_failed.csv` for failed URLs
3. Manually retry failed entries after fixing API issues
