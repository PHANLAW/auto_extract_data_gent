"""
Logging Configuration
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config import get_settings

settings = get_settings()


def sanitize_log_message(message: str) -> str:
    """
    Sanitize log message to handle Unicode characters safely on Windows.
    Replaces non-ASCII characters with ASCII equivalents or removes them.
    """
    try:
        # Try to encode as ASCII with error handling
        return message.encode('ascii', errors='replace').decode('ascii')
    except Exception:
        # Fallback: replace non-ASCII characters
        return ''.join(char if ord(char) < 128 else '?' for char in message)


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that safely handles Unicode characters"""
    
    def emit(self, record):
        try:
            # Sanitize the message before logging
            if hasattr(record, 'msg'):
                record.msg = sanitize_log_message(str(record.msg))
            super().emit(record)
        except UnicodeEncodeError:
            # If still fails, replace with safe message
            try:
                record.msg = sanitize_log_message(str(record.msg))
                super().emit(record)
            except Exception:
                # Last resort: log without the problematic message
                pass


def setup_logging():
    """Setup application logging (idempotent - safe to call multiple times)"""
    
    # Root logger
    root_logger = logging.getLogger()
    
    # Check if logging already configured (has handlers)
    if root_logger.handlers:
        # Logging already configured, just update level
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        return root_logger
    
    # Create logs directory if it doesn't exist
    log_file_path = Path(settings.LOG_FILE)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Console handler with safe Unicode handling
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation and UTF-8 encoding
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'  # Use UTF-8 for file logging
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    return root_logger


# Initialize logging
logger = setup_logging()
