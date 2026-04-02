# Image Processing Agent - Enterprise Edition

Enterprise-grade FastAPI application for processing images, extracting URLs, and managing sports match data with automatic blob storage tracking.

## 🏗️ Architecture

```
app/
├── api/              # FastAPI routes and endpoints
├── agents/          # AI agent framework
├── core/            # Core configuration and utilities
│   └── agent_manager.py  # Agent manager (singleton)
├── models/          # Pydantic schemas
├── services/        # Service layer
│   ├── workflow_service.py  # Workflow orchestration
│   └── blob_tracker.py      # Azure Blob Storage tracker
├── tools/           # Tool management system
└── utils/           # Utility functions

prompts/             # YAML prompt configurations
data/                # Local test data
tests/               # Comprehensive test suite
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
```

### 2. Configuration

Edit `.env` file (see `.env.example` for all options):

**Required:**
```env
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
SPORT_API_BASE_URL=https://your-api.com
SPORT_API_KEY=your-api-key
```

**For Local Testing:**
```env
DATA_SOURCE_MODE=local
LOCAL_DATA_PATH=data
```

**For Blob Storage (Production):**
```env
DATA_SOURCE_MODE=blob_storage
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_BLOB_CONTAINER_NAME=image-folders
AUTO_PROCESS_ENABLED=true
```

### 3. Run Application

```bash
# FastAPI Server
python main.py

# Workflow CLI (Local)
python workflow_cli.py data

# Run Tests (100% coverage required)
pytest
```

## 📋 Features

### ✅ Core Features
- Folder name parsing (extract match info)
- URL extraction from images (Azure OpenAI Vision)
- Link detection and image upload
- Error handling with retry file
- Comprehensive test suite (100% coverage)

### ✅ Enterprise Features
- Agent Manager (singleton pattern, reuse instances)
- Workflow Service (orchestration layer)
- Azure Blob Storage integration
- Auto-processing with tracker
- API trigger for manual check
- YAML prompt configuration

## 🔄 Workflow

1. **Parse folder name** → Extract `match_name`, `league`, `start_time`
2. **Get sport_id** → Call API with match info
3. **For each image**:
   - Extract URL using Azure OpenAI Vision
   - Detect link → Get `detected_link_id`
   - Upload image with `detected_link_id`
4. **Error handling** → Write to `retry_failed.json` if no `detected_link_id`

## 📁 Data Structure

### Local Mode:
```
data/
├── 02.01.26 00:30 PL 25_26 Crystal Palace - Fulham/
│   ├── image1.png
│   └── ...
```

### Blob Storage Mode:
```
Container: image-folders
├── 02.01.26 00:30 PL 25_26 Crystal Palace - Fulham/
│   └── ...
```

## 🧪 Testing

### Run All Tests
```bash
pytest
```

### With Coverage
```bash
pytest --cov=app --cov-report=html
```

### Test Structure
- `tests/unit/` - Unit tests for all components
- `tests/integration/` - Integration tests
- `tests/fixtures/` - Test data fixtures

**Coverage Target: 100%** ✅

## 📡 API Endpoints

- `GET /api/v1/health` - Health check
- `POST /api/v1/parse-folder` - Parse folder name
- `POST /api/v1/process-folder` - Process folder (local)
- `POST /api/v1/process-image` - Process single image
- `POST /api/v1/trigger-blob-check` - Trigger blob storage check
- `GET /api/v1/tools` - List all tools

See API docs at `/docs` when server is running.

## 🔧 Configuration

All configuration in `.env` file (see `.env.example`):

- Azure OpenAI settings
- Sport API settings
- Data source mode (local/blob_storage)
- Auto-processing settings
- Tracker settings

## 📚 Documentation

- `SETUP_GUIDE.md` - Detailed setup guide
- `PROJECT_STRUCTURE.md` - Architecture details
- `TESTING.md` - Testing guide
- `ENTERPRISE_SETUP.md` - Enterprise setup

## 🐳 Docker

```bash
# Build
docker build -t image-processing-agent .

# Run
docker run -p 8000:8000 --env-file .env image-processing-agent

# Or use docker-compose
docker-compose up -d
```

## 📝 Notes

- Folder names must follow format: `dd.mm.yy hh:mm LEAGUE match_name`
- Blob Storage mode auto-cleans downloaded folders after processing
- Tracker state file prevents reprocessing
- Auto-processing only runs when enabled and in blob_storage mode

## 🔒 Production Considerations

1. Set proper CORS origins
2. Use environment variables for secrets
3. Configure proper logging
4. Set up monitoring
5. Use HTTPS in production
