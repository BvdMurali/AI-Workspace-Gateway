"""
AI Workspace Gateway - Logging Service
Provides structured logging support with JSON or pretty formatting.
"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""
    
    STANDARD_FIELDS = {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module",
        "msecs", "message", "msg", "name", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "thread", "threadName"
    }

    def format(self, record: logging.LogRecord) -> str:
        # Resolve message
        message = record.getMessage()
        
        # Build base payload
        log_payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        
        # Parse exception if exists
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
            
        # Extract any extra fields passed in logging
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_FIELDS and not key.startswith("_"):
                log_payload[key] = value
                
        return json.dumps(log_payload)


class LoggingService:
    """Configures system-wide logging based on configuration options."""

    def __init__(self, level: str = "INFO", log_format: str = "json", destination: str = "stdout"):
        self.level_str = level.upper()
        self.log_format = log_format.lower()
        self.destination = destination
        self.logger = logging.getLogger("gateway")
        self._configure()

    def _configure(self) -> None:
        """Configures root and gateway loggers with handlers and formatters."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Resolve logging level
        level = getattr(logging, self.level_str, logging.INFO)
        self.logger.setLevel(level)
        
        # Create formatter
        if self.log_format == "json":
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        # Resolve destination handler
        if self.destination == "stdout":
            handler = logging.StreamHandler(sys.stdout)
        elif self.destination == "stderr":
            handler = logging.StreamHandler(sys.stderr)
        else:
            # Assume destination is a file path
            log_file = Path(self.destination)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            # Setup rotating file handler for future log rotation
            handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024, # 10MB default limit per file
                backupCount=5, # Keep up to 5 files
                encoding="utf-8"
            )
            
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Set root logger level to match (to capture third party logs if necessary)
        logging.getLogger().setLevel(logging.WARNING)

    def get_logger(self) -> logging.Logger:
        """Returns the configured logger instance."""
        return self.logger
