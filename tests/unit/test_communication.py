"""
AI Workspace Gateway - Sprint 2 Communication Layer Unit & Integration Tests
"""

import asyncio
from datetime import datetime, timezone, timedelta
import time
from typing import Generator
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import status, FastAPI, APIRouter, Depends
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
import pytest

from apps.gateway.api.app import create_app
from apps.gateway.bootstrap.lifecycle import Lifecycle
from apps.gateway.utils.exceptions import (
    GatewayError,
    WorkspaceError,
    ProviderError,
    ValidationError,
    StorageError,
    ConfigurationError,
    map_exception
)
from apps.gateway.utils.envelope import MessageEnvelope, create_error_payload
from apps.gateway.services.connection_manager import ConnectionManager, Connection
from apps.gateway.services.event_bridge import EventBridge
from apps.gateway.events.bus import EventBus


# ======================================================================
# Phase 1 Tests: Exceptions & Error Mapping
# ======================================================================

def test_exception_classes() -> None:
    """Verifies instantiation and attribute assignment of custom exceptions."""
    exc = WorkspaceError("Workspace locked", code="WORKSPACE_IS_LOCKED", status_code=403, details={"workspace_id": "123"})
    assert isinstance(exc, GatewayError)
    assert exc.message == "Workspace locked"
    assert exc.code == "WORKSPACE_IS_LOCKED"
    assert exc.status_code == 403
    assert exc.details == {"workspace_id": "123"}
    assert exc.retryable is False

    exc_net = ProviderError("Rate limit exceeded", code="PROVIDER_RATE_LIMIT", status_code=429)
    assert exc_net.status_code == 429
    assert exc_net.retryable is False


def test_map_exception() -> None:
    """Tests exception translator under different types of inputs."""
    # Custom Gateway Error
    g_err = WorkspaceError("Error")
    assert map_exception(g_err) is g_err

    # ValueError
    v_err = ValueError("Value invalid")
    mapped_v = map_exception(v_err)
    assert mapped_v.code == "REQUEST_BODY_INVALID"
    assert mapped_v.status_code == 422

    # TimeoutError
    t_err = TimeoutError("Timed out")
    mapped_t = map_exception(t_err)
    assert mapped_t.code == "PROVIDER_CONNECT_TIMEOUT"
    assert mapped_t.status_code == 504

    # StorageError string parsing
    from apps.gateway.storage.bootstrap import StorageError as NativeStorageError
    disk_err = NativeStorageError("disk space exhausted")
    mapped_d = map_exception(disk_err)
    assert mapped_d.code == "DISK_SPACE_EXHAUSTED"
    assert mapped_d.status_code == 507

    db_err = NativeStorageError("SQLite error")
    mapped_db = map_exception(db_err)
    assert mapped_db.code == "DATABASE_ERROR"
    assert mapped_db.status_code == 500

    # ConfigurationError
    from apps.gateway.config.manager import ConfigurationError as NativeConfigError
    config_err = NativeConfigError("Invalid yaml")
    mapped_c = map_exception(config_err)
    assert mapped_c.code == "CONFIGURATION_ERROR"
    assert mapped_c.status_code == 500


# ======================================================================
# Phase 2 Tests: Message Envelope
# ======================================================================

def test_message_envelope_lifecycle() -> None:
    """Validates envelope schema field validation, generation, and default fields."""
    env = MessageEnvelope(type="ping")
    assert env.type == "ping"
    assert env.version == "v1"
    assert env.id is not None
    assert env.timestamp is not None
    assert env.payload == {}

    data = {
        "type": "subscribe",
        "correlation_id": "corr-123",
        "payload": {"topic": "system.*"}
    }
    env_parsed = MessageEnvelope.model_validate(data)
    assert env_parsed.type == "subscribe"
    assert env_parsed.correlation_id == "corr-123"
    assert env_parsed.payload == {"topic": "system.*"}

    with pytest.raises(PydanticValidationError):
        # Missing type
        MessageEnvelope.model_validate({"payload": {}})


# ======================================================================
# Phase 3 Tests: Connection Manager & Cleanup
# ======================================================================

@pytest.mark.asyncio
async def test_connection_manager_operations() -> None:
    """Verifies connection lifecycle tracking and idle timeouts."""
    mock_ws = AsyncMock()
    manager = ConnectionManager(idle_timeout_seconds=0.2, cleanup_interval_seconds=0.05)
    
    # 1. Connect
    conn = manager.connect("c1", "client-1", mock_ws)
    assert conn.connection_id == "c1"
    assert conn.client_id == "client-1"
    assert "c1" in manager.active_connections

    # 2. Heartbeat update
    assert manager.update_heartbeat("c1") is True
    assert manager.update_heartbeat("unknown") is False

    # 3. Subscriptions
    assert manager.subscribe("c1", "system.cpu") is True
    assert "system.cpu" in manager.active_connections["c1"].subscriptions
    
    assert manager.unsubscribe("c1", "system.cpu") is True
    assert "system.cpu" not in manager.active_connections["c1"].subscriptions

    # 4. Connection to dict
    c_dict = conn.to_dict()
    assert c_dict["connection_id"] == "c1"
    assert "last_heartbeat" in c_dict

    # 5. Idle Timeout Cleanup
    await manager.start()
    # Wait for timeout
    await asyncio.sleep(0.35)
    
    # Verify cleaned up
    assert "c1" not in manager.active_connections
    await manager.stop()


# ======================================================================
# Phase 4 Tests: Event Bridge
# ======================================================================

@pytest.mark.asyncio
async def test_event_bridge_routing() -> None:
    """Tests that EventBridge maps EventBus events to matching client subscriptions."""
    bus = EventBus()
    manager = ConnectionManager()
    bridge = EventBridge(event_bus=bus, connection_manager=manager)
    
    mock_ws_1 = AsyncMock()
    mock_ws_2 = AsyncMock()
    
    # Register connections
    conn1 = manager.connect("c1", "client-1", mock_ws_1)
    conn2 = manager.connect("c2", "client-2", mock_ws_2)
    
    # Subscriptions
    manager.subscribe("c1", "system.*")
    manager.subscribe("c2", "storage.#")
    
    bridge.start()
    
    # Publish non-matching event
    await bus.publish("other.topic", {"data": 1})
    assert mock_ws_1.send_json.call_count == 0
    assert mock_ws_2.send_json.call_count == 0

    # Publish matching event for conn1
    await bus.publish("system.cpu", {"usage": 45.2})
    # Wait short instant for async task processing
    await asyncio.sleep(0.05)
    assert mock_ws_1.send_json.call_count == 1
    assert mock_ws_2.send_json.call_count == 0
    
    sent_data = mock_ws_1.send_json.call_args[0][0]
    assert sent_data["type"] == "system.cpu"
    assert sent_data["payload"] == {"usage": 45.2}

    # Publish matching event for conn2 (wildcard recursive)
    await bus.publish("storage.disk.critical", {"bytes": 0})
    await asyncio.sleep(0.05)
    assert mock_ws_2.send_json.call_count == 1

    bridge.stop()


# ======================================================================
# Setup Fixture for App tests
# ======================================================================

@pytest.fixture
def test_app(tmp_path) -> Generator[FastAPI, None, None]:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # Low rate limit & idle timeouts for testing
    default_yaml = f"""
server:
  host: "127.0.0.1"
  port: 8080
  rateLimitCapacity: 20
  rateLimitPeriodSeconds: 60
  idleTimeoutSeconds: 0.5
  cleanupIntervalSeconds: 0.1
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
    
    from pydantic import BaseModel
    
    class DummyItem(BaseModel):
        name: str
        value: int

    # Add a dummy endpoint to test exceptions recovery
    @app.get("/test-error")
    def trigger_error():
        raise WorkspaceError("Resource is locked", code="WORKSPACE_IS_LOCKED", status_code=403)

    @app.get("/test-runtime-error")
    def trigger_runtime():
        raise RuntimeError("Crash")

    @app.post("/test-validation")
    def trigger_validation(item: DummyItem):
        return {"status": "ok"}

    yield app


# ======================================================================
# Phase 5 Tests: REST APIs, Middlewares, and Doc Rendering
# ======================================================================

def test_rest_endpoints(test_app) -> None:
    """Verifies REST endpoints and versioning structure."""
    with TestClient(test_app) as client:
        # V1 endpoints
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "healthy"

        response = client.get("/api/v1/ready")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ready"}

        response = client.get("/api/v1/version")
        assert response.status_code == status.HTTP_200_OK
        assert "version" in response.json()

        # OpenAPI schema
        response = client.get("/api/v1/openapi")
        assert response.status_code == status.HTTP_200_OK
        schema = response.json()
        assert "openapi" in schema
        assert schema["info"]["title"] == "AI Workspace Gateway v1"

        # Swagger & Redoc
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "html" in response.headers["content-type"]

        response = client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK
        assert "html" in response.headers["content-type"]


def test_middlewares_headers_and_logs(test_app) -> None:
    """Validates that RequestID, timing, security, compression, and logging headers are injected."""
    with TestClient(test_app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Headers check
        assert "X-Request-ID" in response.headers
        assert "X-Correlation-ID" in response.headers
        assert "X-Response-Time-Ms" in response.headers
        
        # Security headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "Strict-Transport-Security" in response.headers


def test_rate_limiting_middleware(test_app) -> None:
    """Tests the token bucket rate limiting limits excessive calls."""
    with TestClient(test_app) as client:
        # Limit capacity is 20 requests per minute
        headers = {"Client-ID": "test-client"}
        for _ in range(20):
            res = client.get("/api/v1/health", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            
        # The 21st request should fail
        res = client.get("/api/v1/health", headers=headers)
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = res.json()
        assert data["code"] == "PROVIDER_RATE_LIMIT"


def test_error_recovery_middleware(test_app) -> None:
    """Ensures exceptions raised in endpoints map to structured error payloads."""
    with TestClient(test_app) as client:
        # 1. Custom GatewayError
        response = client.get("/test-error")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["code"] == "WORKSPACE_IS_LOCKED"
        assert data["message"] == "Resource is locked"
        
        # 2. General unhandled exception
        response = client.get("/test-runtime-error")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["code"] == "INTERNAL_SERVER_ERROR"

        # 3. RequestValidationError mapping check
        response = client.post("/test-validation", json={"name": "test"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["code"] == "REQUEST_BODY_INVALID"


# ======================================================================
# Phase 6 Tests: WebSocket Connection and Lifecycle
# ======================================================================

def test_websocket_lifecycle_and_messages(test_app) -> None:
    """Tests WebSocket lifecycle, ping/pong, subscribe/unsubscribe, and invalid frames."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws?clientId=tester") as websocket:
            
            # 1. Ping / Pong
            websocket.send_json({
                "type": "ping",
                "id": "ping-1"
            })
            resp = websocket.receive_json()
            assert resp["type"] == "pong"
            assert resp["correlation_id"] == "ping-1"

            # 2. Invalid Envelope
            websocket.send_json({
                # Missing type
                "correlation_id": "err-1"
            })
            resp = websocket.receive_json()
            assert resp["type"] == "session.error"
            assert resp["payload"]["code"] == "MESSAGE_ENVELOPE_INVALID"

            # 3. Subscribe
            websocket.send_json({
                "type": "subscribe",
                "id": "sub-1",
                "payload": {"topic": "test.topic"}
            })
            resp = websocket.receive_json()
            assert resp["type"] == "subscribe.ack"
            assert resp["payload"]["topic"] == "test.topic"

            # 4. Subscribe (Missing topic)
            websocket.send_json({
                "type": "subscribe",
                "id": "sub-2",
                "payload": {}
            })
            resp = websocket.receive_json()
            assert resp["type"] == "session.error"
            assert resp["payload"]["code"] == "SUBSCRIBE_MISSING_TOPIC"

            # 5. Unsubscribe
            websocket.send_json({
                "type": "unsubscribe",
                "id": "unsub-1",
                "payload": {"topic": "test.topic"}
            })
            resp = websocket.receive_json()
            assert resp["type"] == "unsubscribe.ack"
            assert resp["payload"]["topic"] == "test.topic"

            # 6. Unsubscribe (Missing topic)
            websocket.send_json({
                "type": "unsubscribe",
                "id": "unsub-2",
                "payload": {}
            })
            resp = websocket.receive_json()
            assert resp["type"] == "session.error"
            assert resp["payload"]["code"] == "UNSUBSCRIBE_MISSING_TOPIC"

            # 7. Unsupported Message Type
            websocket.send_json({
                "type": "unsupported_command",
                "id": "unsupp-1"
            })
            resp = websocket.receive_json()
            assert resp["type"] == "session.error"
            assert resp["payload"]["code"] == "UNSUPPORTED_MESSAGE_TYPE"
