"""
AI Workspace Gateway - Health and API Endpoints Unit Tests
"""

from pathlib import Path
from unittest.mock import patch
from fastapi import status
from fastapi.testclient import TestClient
import pytest
from apps.gateway.api.app import create_app
from apps.gateway.bootstrap.lifecycle import Lifecycle


def test_health_endpoints(tmp_path: Path) -> None:
    """Verifies that the /health, /ready, and /version endpoints behave correctly under TestClient context."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # Configure custom configs for testing
    default_yaml = f"""
server:
  host: "127.0.0.1"
  port: 8080
storage:
  dataDir: "{tmp_path / 'data'}"
  encryptionEnabled: false
logging:
  level: "info"
  format: "json"
  destination: "stdout"
telemetry:
  enabled: false
"""
    (config_dir / "default.yaml").write_text(default_yaml, encoding="utf-8")
    
    # Initialize Lifecycle and Application
    lifecycle = Lifecycle(config_dir=config_dir)
    app = create_app(lifecycle)
    
    # Use TestClient context manager to trigger lifespan events
    with TestClient(app) as client:
        # 1. Test /ready
        response = client.get("/ready")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ready"}
        
        # 2. Test /health
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "healthy"
        assert "usage" in data
        assert "memory_mb" in data["usage"]
        assert "disk" in data["usage"]
        
        # 3. Test /version
        response = client.get("/version")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"version": "0.1.0"}
        
        # 4. Test /api/v1 prefix
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK


def test_readiness_before_startup() -> None:
    """Verifies /ready endpoint returns 503 if the system lifecycle has not started."""
    lifecycle = Lifecycle()
    app = create_app(lifecycle)
    
    # Note: we are NOT using the client context manager here, so lifespan startup doesn't run
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "not_ready"}


@pytest.mark.asyncio
async def test_health_service_memory_warning(tmp_path: Path) -> None:
    """Verifies that the HealthService publishes a critical system event if memory exceeds threshold."""
    from apps.gateway.events.bus import EventBus
    from apps.gateway.storage.bootstrap import StorageBootstrap
    from apps.gateway.health.service import HealthService
    
    # Setup mocks
    storage = StorageBootstrap(str(tmp_path))
    storage.initialize()
    
    bus = EventBus()
    events = []
    bus.subscribe("system.resource.critical", lambda t, e: events.append(e))
    
    health = HealthService(storage_bootstrap=storage, event_bus=bus, data_dir=str(tmp_path))
    
    # Set limit to 0 MB to trigger critical memory warning
    health.memory_limit_mb = 0.0
    
    status_res = await health.check_health()
    
    assert len(events) == 1
    assert events[0]["metric"] == "memory"
    assert events[0]["limit_mb"] == 0.0
    
    storage.close()


@pytest.mark.asyncio
async def test_health_service_disk_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies HealthService behaves correctly when disk_usage check raises an exception."""
    import shutil
    from apps.gateway.events.bus import EventBus
    from apps.gateway.storage.bootstrap import StorageBootstrap
    from apps.gateway.health.service import HealthService
    
    storage = StorageBootstrap(str(tmp_path))
    storage.initialize()
    
    bus = EventBus()
    
    # Force disk usage to raise an error
    def mock_disk_usage(path: str) -> None:
        raise OSError("Disk full or missing")
        
    monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)
    
    health = HealthService(storage_bootstrap=storage, event_bus=bus, data_dir=str(tmp_path))
    status_res = await health.check_health()
    
    # Status should still check out, but disk usage dict is empty
    assert status_res["status"] == "ok"
    assert status_res["usage"]["disk"] == {}
    
    storage.close()


def test_health_endpoint_db_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies health API returns 503 if database check fails."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    default_yaml = f"""
server:
  host: "127.0.0.1"
  port: 8080
storage:
  dataDir: "{tmp_path / 'data'}"
  encryptionEnabled: false
logging:
  level: "info"
  format: "json"
  destination: "stdout"
telemetry:
  enabled: false
"""
    (config_dir / "default.yaml").write_text(default_yaml, encoding="utf-8")
    
    lifecycle = Lifecycle(config_dir=config_dir)
    app = create_app(lifecycle)
    
    with TestClient(app) as client:
        with patch("apps.gateway.storage.bootstrap.StorageBootstrap.check_health", return_value=False):
            response = client.get("/health")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert response.json()["status"] == "error"
            assert response.json()["database"] == "unhealthy"


