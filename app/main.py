"""
FastAPI Application Entry Point
"""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging_config import logger, setup_logging
from app.api.routes import router
from app.services.blob_tracker import BlobTracker
from app.services.processing_manager import ProcessingManager

settings = get_settings()

# Initialize logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise Image Processing Agent with FastAPI",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix=settings.API_V1_PREFIX, tags=["v1"])


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"API docs available at /docs")
    
    # Start auto processing if enabled and state allows
    if settings.DATA_SOURCE_MODE == "blob_storage":
        processing_manager = ProcessingManager()
        if processing_manager.is_blob_auto_enabled():
            tracker = BlobTracker()
            # Start auto processing in background
            asyncio.create_task(tracker.start_auto_processing())
            logger.info("Blob auto-processing started")
        else:
            logger.info("Blob auto-processing is disabled (use /api/v1/processing/blob-auto to enable)")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down application")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "data_source_mode": settings.DATA_SOURCE_MODE,
        "auto_processing": settings.AUTO_PROCESS_ENABLED
    }
