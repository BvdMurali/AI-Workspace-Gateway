"""
AI Workspace Gateway - Logging Service Unit Tests
"""

import json
import logging
from pathlib import Path
from apps.gateway.logging.service import LoggingService


def test_json_logger_output(tmp_path: Path) -> None:
    """Verifies that the logging service outputs valid JSON logs with extra fields."""
    log_file = tmp_path / "test_json.log"
    
    # Initialize logger
    logging_service = LoggingService(
        level="DEBUG",
        log_format="json",
        destination=str(log_file)
    )
    logger = logging_service.get_logger()
    
    logger.info("Application starting", extra={"step": "boot", "code": 100})
    
    # Shut down logging to flush and close file handles
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)
        
    log_content = log_file.read_text(encoding="utf-8").strip()
    assert log_content != ""
    
    # Parse log as JSON
    log_entry = json.loads(log_content)
    assert log_entry["level"] == "INFO"
    assert log_entry["logger"] == "gateway"
    assert log_entry["message"] == "Application starting"
    assert log_entry["step"] == "boot"
    assert log_entry["code"] == 100
    assert "timestamp" in log_entry


def test_pretty_logger_output(tmp_path: Path) -> None:
    """Verifies pretty log formatting."""
    log_file = tmp_path / "test_pretty.log"
    
    logging_service = LoggingService(
        level="WARNING",
        log_format="pretty",
        destination=str(log_file)
    )
    logger = logging_service.get_logger()
    
    logger.warning("Something might be wrong")
    
    # Shut down logging
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)
        
    log_content = log_file.read_text(encoding="utf-8").strip()
    assert "WARNING" in log_content
    assert "Something might be wrong" in log_content
