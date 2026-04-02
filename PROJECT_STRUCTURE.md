# Project Structure

## Enterprise Image Processing Agent

This document describes the enterprise project structure.

## Directory Layout

```
extract-img-to-text/
│
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   │
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   ├── routes.py             # FastAPI route definitions
│   │   └── dependencies.py       # Dependency injection
│   │
│   ├── agents/                   # Agent framework
│   │   ├── __init__.py
│   │   └── image_processing_agent.py  # Main agent implementation
│   │
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration management (Pydantic Settings)
│   │   ├── logging_config.py     # Logging setup
│   │   └── prompt_loader.py      # YAML prompt loader
│   │
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic schemas for API
│   │
│   ├── tools/                    # Tool management system
│   │   ├── __init__.py
│   │   ├── base.py               # Base tool interface
│   │   ├── url_extractor_tool.py    # URL extraction tool
│   │   ├── api_tools.py          # API interaction tools
│   │   └── tool_manager.py       # Tool registry and manager
│   │
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── folder_parser.py      # Folder name parser
│       ├── sport_api.py          # Sport API client
│       └── error_handler.py      # Error handling and retry file management
│
├── prompts/                      # YAML prompt configurations
│   └── url_extraction.yaml       # URL extraction prompt
│
├── config/                       # Configuration files
│   └── __init__.py
│
├── logs/                         # Application logs (created at runtime)
│
├── main.py                       # Application entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker container definition
├── docker-compose.yml            # Docker Compose configuration
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
│
├── README.md                     # Main documentation
├── PROJECT_STRUCTURE.md          # This file
└── QUICK_START.md                # Quick start guide
```

## Component Descriptions

### API Layer (`app/api/`)

- **routes.py**: Defines all FastAPI endpoints
  - Health check
  - Folder parsing
  - Image processing
  - Tool listing

- **dependencies.py**: Dependency injection for FastAPI
  - Azure OpenAI client
  - Sport API client
  - Agent instances
  - Error handler

### Agent Framework (`app/agents/`)

- **image_processing_agent.py**: Main agent orchestrating:
  1. URL extraction from images
  2. Link detection via API
  3. Image upload
  4. Error handling

### Core (`app/core/`)

- **config.py**: Centralized configuration using Pydantic Settings
  - Environment variable loading
  - Type validation
  - Default values

- **logging_config.py**: Logging setup
  - Console and file handlers
  - Log rotation
  - Configurable log levels

- **prompt_loader.py**: YAML prompt loader
  - Caching
  - Hot reload support
  - Model configuration

### Models (`app/models/`)

- **schemas.py**: Pydantic models for:
  - API request/response validation
  - Type safety
  - API documentation

### Tools (`app/tools/`)

- **base.py**: Abstract base class for all tools
- **url_extractor_tool.py**: Azure OpenAI Vision integration
- **api_tools.py**: API interaction tools
- **tool_manager.py**: Tool registry and execution

### Utils (`app/utils/`)

- **folder_parser.py**: Parse folder names to extract match info
- **sport_api.py**: Sport API client wrapper
- **error_handler.py**: Error handling and retry file management

## Key Features

### 1. Modular Architecture
- Separation of concerns
- Easy to extend
- Testable components

### 2. Configuration Management
- Environment variables
- Pydantic validation
- YAML prompts

### 3. Tool System
- Pluggable tools
- Tool registry
- Schema generation

### 4. Agent Framework
- Orchestrates tool execution
- Error handling
- Logging

### 5. API Layer
- RESTful endpoints
- OpenAPI documentation
- Type validation

## Adding New Components

### Adding a New Tool

1. Create tool class in `app/tools/`:
```python
from app.tools.base import BaseTool

class MyTool(BaseTool):
    def execute(self, **kwargs):
        # Implementation
        pass
```

2. Register in tool manager (auto-registered via agent)

### Adding a New Prompt

1. Create YAML file in `prompts/`:
```yaml
name: my_prompt
prompt: |
  Your prompt text
model_config:
  max_tokens: 300
```

2. Load in code:
```python
from app.core.prompt_loader import prompt_loader
prompt = prompt_loader.get_prompt_text("my_prompt")
```

### Adding a New API Endpoint

1. Add route in `app/api/routes.py`:
```python
@router.post("/my-endpoint")
async def my_endpoint(request: MyRequest):
    # Implementation
    pass
```

2. Add schema in `app/models/schemas.py`

## Configuration Flow

1. Environment variables (`.env`) → `app/core/config.py`
2. YAML prompts (`prompts/`) → `app/core/prompt_loader.py`
3. Configuration → Dependency injection → Components

## Data Flow

1. **API Request** → `app/api/routes.py`
2. **Validation** → `app/models/schemas.py`
3. **Dependency Injection** → `app/api/dependencies.py`
4. **Agent Processing** → `app/agents/image_processing_agent.py`
5. **Tool Execution** → `app/tools/`
6. **Response** → API client

## Error Handling Flow

1. Tool execution error
2. Agent catches error
3. Error handler writes to retry file
4. Error response returned to API

## Logging Flow

1. Components log via `app/core/logging_config.py`
2. Logs written to console and file
3. Rotating file handler (10MB, 5 backups)
