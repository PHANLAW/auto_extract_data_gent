# Quick Start Guide

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requements.txt
   ```

2. **Configure Azure OpenAI** (in `main_workflow.py`)
   ```python
   AZURE_OPENAI_API_KEY = "your-key-here"
   AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.com"
   ```

3. **Configure Sport API** (in `sport_api.py`)
   ```python
   SPORT_API_BASE_URL = "https://your-api.com"
   SPORT_API_KEY = "your-api-key"  # If required
   ```

4. **Update API Endpoints** (in `sport_api.py`)
   - `get_sport_id()`: Your endpoint for getting sport_id
   - `detect_link()`: Your endpoint for detecting links
   - `upload_image()`: Your endpoint for uploading images

## Usage

### Process All Folders

```bash
python main_workflow.py
```

Make sure to set `BASE_FOLDER` in `main_workflow.py` to point to your folder containing match folders.

### Process Single Folder (Python)

```python
from main_workflow import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
result = orchestrator.process_folder("./02.01.26 00:30 PL 25_26 Crystal Palace - Fulham")
print(result)
```

## Folder Structure

```
base_folder/
├── 02.01.26 00:30 PL 25_26 Crystal Palace - Fulham/
│   ├── image1.png
│   ├── image2.png
│   └── ...
├── 15.12.25 14:30 EPL 24_25 Manchester United - Liverpool/
│   ├── image1.png
│   └── ...
└── ...
```

## Workflow

1. **Parse folder name** → Extract match_name, league, start_time
2. **Call API** → Get sport_id using match_name, league, start_time
3. **For each image**:
   - Extract URL using Azure OpenAI Vision
   - Call API to detect link → Get detected_link_id
   - Upload image with detected_link_id
4. **Error handling** → If detected_link_id not found, write to `retry_failed.json`

## Output Files

- `workflow_results.json`: Complete processing results
- `retry_failed.json`: Failed URLs for manual retry
- `workflow_log.txt`: Processing logs

## Testing

Test folder parser:
```bash
python folder_parser.py
```

Test error handler:
```bash
python example_usage.py
```

## Troubleshooting

### Folder name not parsing?
- Check format: `dd.mm.yy hh:mm LEAGUE match_name`
- Example: `02.01.26 00:30 PL 25_26 Crystal Palace - Fulham`

### API errors?
- Verify API endpoints in `sport_api.py`
- Check API response format matches expected structure
- Review `workflow_log.txt` for detailed errors

### URL extraction failing?
- Verify Azure OpenAI credentials
- Check image files are readable
- Ensure vision model is deployed
