"""
AI Workspace Gateway - Telemetry Unit Tests
"""

import json
from pathlib import Path
import pytest
from apps.gateway.telemetry.bootstrap import TelemetryBootstrap, TelemetryService


def test_telemetry_client_id_persistence(tmp_path: Path) -> None:
    """Verifies that the telemetry service creates and persists a hashed client ID."""
    data_dir = tmp_path / "data"
    config = {"telemetry": {"enabled": True, "endpoint": "http://localhost"}}
    
    # 1. Initialize first time
    bootstrap = TelemetryBootstrap(config, str(data_dir))
    service_1 = bootstrap.initialize()
    client_id_1 = service_1.client_id
    
    assert client_id_1 is not None
    assert len(client_id_1) == 64  # SHA-256 hex digest length
    
    # 2. Re-initialize and verify the client ID is persistent and matching
    service_2 = bootstrap.initialize()
    client_id_2 = service_2.client_id
    
    assert client_id_1 == client_id_2
    
    # Check that .client_id file exists in data directory
    assert (data_dir / ".client_id").exists()


def test_telemetry_client_id_write_error(tmp_path: Path) -> None:
    """Verifies fallback client ID generation when directory is write-protected."""
    # Using a path that can't be created or written to (e.g. empty or restricted)
    invalid_dir = Path("/dev/null/invalid_path")
    config = {"telemetry": {"enabled": True, "endpoint": "http://localhost"}}
    
    bootstrap = TelemetryBootstrap(config, str(invalid_dir))
    service = bootstrap.initialize()
    
    assert service.client_id is not None
    assert len(service.client_id) == 64


def test_telemetry_record_event_privacy_stripping(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Verifies that record_event strips sensitive properties and records only approved metrics."""
    data_dir = tmp_path / "data"
    config = {"telemetry": {"enabled": True, "endpoint": "http://localhost"}}
    
    import logging
    logger = logging.getLogger("gateway")
    logger.setLevel(logging.INFO)
    
    bootstrap = TelemetryBootstrap(config, str(data_dir), logger=logger)
    service = bootstrap.initialize()
    
    # Test record with both approved and unapproved fields
    metrics = {
        "latency_ms": 120,
        "error_code": "SQLITE_FULL",
        "sensitive_user_prompt": "Drop database!",  # Should be stripped
        "session_id": "123-abc",  # Should be stripped
    }
    
    with caplog.at_level(logging.INFO, logger="gateway"):
        service.record_event("session.started", metrics)
        
    # Verify that log message has recorded event and stripped sensitive parameters
    record_logs = [rec.message for rec in caplog.records if "Telemetry Event Recorded" in rec.message]
    assert len(record_logs) == 1
    
    # Extract telemetry dictionary from record log fields if present or check extra attributes
    extra_data = [rec.telemetry for rec in caplog.records if hasattr(rec, "telemetry")]
    assert len(extra_data) == 1
    
    payload = extra_data[0]
    assert payload["event"] == "session.started"
    assert "latency_ms" in payload["metrics"]
    assert "error_code" in payload["metrics"]
    assert "sensitive_user_prompt" not in payload["metrics"]
    assert "session_id" not in payload["metrics"]


def test_telemetry_disabled(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Verifies that record_event does nothing when telemetry is disabled."""
    data_dir = tmp_path / "data"
    config = {"telemetry": {"enabled": False, "endpoint": "http://localhost"}}
    
    bootstrap = TelemetryBootstrap(config, str(data_dir))
    service = bootstrap.initialize()
    
    with caplog.at_level("INFO"):
        service.record_event("session.started", {"latency_ms": 10})
        
    record_logs = [rec.message for rec in caplog.records if "Telemetry Event Recorded" in rec.message]
    assert len(record_logs) == 0
    
    # Shutdown test
    service.shutdown()
