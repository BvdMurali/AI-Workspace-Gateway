"""
AI Workspace Gateway - Execution Framework Unit Tests
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Generator
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from apps.gateway.api.app import create_app
from apps.gateway.bootstrap.lifecycle import Lifecycle
from apps.gateway.core.execution.models import Execution, ExecutionState, RetryPolicy
from apps.gateway.core.execution.state_machine import ExecutionStateMachine
from apps.gateway.core.execution.validation import ExecutionValidation
from apps.gateway.core.execution.repository import ExecutionRepository
from apps.gateway.core.execution.scheduler import ExecutionScheduler
from apps.gateway.core.execution.service import ExecutionService
from apps.gateway.core.execution.manager import ExecutionManager
from apps.gateway.core.execution.exceptions import (
    ExecutionError, ExecutionNotFoundError, InvalidStateTransitionError, ExecutionValidationError
)
from apps.gateway.events.bus import EventBus
from apps.gateway.storage.bootstrap import StorageBootstrap


# ======================================================================
# Phase 1: State Machine & Validation Tests
# ======================================================================

def test_execution_state_machine_transitions() -> None:
    """Verifies valid state transitions and rejection of invalid transitions."""
    # Test valid transitions
    ExecutionStateMachine.validate_transition(ExecutionState.CREATED, ExecutionState.QUEUED)
    ExecutionStateMachine.validate_transition(ExecutionState.QUEUED, ExecutionState.RUNNING)
    ExecutionStateMachine.validate_transition(ExecutionState.RUNNING, ExecutionState.COMPLETED)
    
    # Test invalid transitions
    with pytest.raises(InvalidStateTransitionError):
        ExecutionStateMachine.validate_transition(ExecutionState.CREATED, ExecutionState.COMPLETED)
        
    with pytest.raises(InvalidStateTransitionError):
        ExecutionStateMachine.validate_transition(ExecutionState.COMPLETED, ExecutionState.RUNNING)
        
    with pytest.raises(InvalidStateTransitionError):
        ExecutionStateMachine.validate_transition(ExecutionState.FAILED, ExecutionState.QUEUED)

    # Test terminal state completed_at update
    exec_obj = Execution()
    assert exec_obj.completed_at is None
    
    ExecutionStateMachine.transition(exec_obj, ExecutionState.RUNNING)
    assert exec_obj.state == ExecutionState.RUNNING
    assert exec_obj.completed_at is None
    
    ExecutionStateMachine.transition(exec_obj, ExecutionState.COMPLETED)
    assert exec_obj.state == ExecutionState.COMPLETED
    assert exec_obj.completed_at is not None


def test_execution_validation_rules() -> None:
    """Verifies that validation enforces required fields and bounds."""
    # Test valid creation validation
    exec_obj = Execution()
    ExecutionValidation.validate_create(exec_obj)
    
    # Test invalid UUID format
    exec_obj.id = "not-a-uuid"
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.id = "4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5"  # restore
    
    # Test invalid state on create
    exec_obj.state = ExecutionState.RUNNING
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.state = ExecutionState.CREATED  # restore

    # Test invalid timeout
    exec_obj.timeout = 0.0
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.timeout = 300.0  # restore
    
    # Test invalid retry policy
    exec_obj.retry_policy.max_retries = -1
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.retry_policy.max_retries = 3  # restore


# ======================================================================
# Setup Repository and Services Fixture
# ======================================================================

@pytest.fixture
def temp_storage(tmp_path) -> Generator[StorageBootstrap, None, None]:
    data_dir = tmp_path / "data"
    bootstrap = StorageBootstrap(data_dir=str(data_dir))
    bootstrap.initialize()
    yield bootstrap
    bootstrap.close()


@pytest.fixture
def event_bus() -> EventBus:
    bus = EventBus()
    yield bus
    bus.shutdown()


@pytest.fixture
def repository(temp_storage) -> ExecutionRepository:
    return ExecutionRepository(temp_storage)


@pytest.fixture
def scheduler(repository, event_bus) -> ExecutionScheduler:
    return ExecutionScheduler(repository, event_bus)


@pytest.fixture
def service(repository, event_bus) -> ExecutionService:
    return ExecutionService(repository, event_bus)


@pytest.fixture
def manager(service, scheduler) -> ExecutionManager:
    return ExecutionManager(service, scheduler)


# ======================================================================
# Phase 2: Repository Tests
# ======================================================================

def test_execution_repository_crud(repository) -> None:
    """Verifies CREATE, READ, UPDATE, and DELETE operations in SQL."""
    exec_obj = Execution(
        workspace_id="w-123",
        provider_id="ollama",
        tool_id="terminal",
        priority=5,
        owner="tester",
        environment_variables={"PATH": "/bin"},
        metadata={"step": 1, "nested": {"val": True}},
        tags=["ai", "test"]
    )
    
    # 1. CREATE
    saved = repository.create(exec_obj)
    assert saved.id == exec_obj.id
    
    # 2. READ
    loaded = repository.get_by_id(exec_obj.id)
    assert loaded is not None
    assert loaded.workspace_id == "w-123"
    assert loaded.provider_id == "ollama"
    assert loaded.tool_id == "terminal"
    assert loaded.priority == 5
    assert loaded.owner == "tester"
    assert loaded.environment_variables == {"PATH": "/bin"}
    assert loaded.metadata == {"step": 1, "nested": {"val": True}}
    assert loaded.tags == ["ai", "test"]
    assert loaded.state == ExecutionState.CREATED

    # 3. UPDATE
    loaded.priority = 10
    loaded.metadata["step"] = 2
    loaded.tags.append("updated")
    
    updated = repository.update(loaded)
    assert updated.priority == 10
    assert updated.metadata["step"] == 2
    assert "updated" in updated.tags
    
    # Verify loaded matches
    loaded_again = repository.get_by_id(exec_obj.id)
    assert loaded_again.priority == 10
    assert loaded_again.metadata["step"] == 2
    
    # 4. DELETE
    assert repository.delete(exec_obj.id) is True
    assert repository.get_by_id(exec_obj.id) is None
    assert repository.delete(exec_obj.id) is False


def test_execution_repository_list_and_search(repository) -> None:
    """Verifies search index filtering on states, workspace, correlation ID, tags, and metadata."""
    e1 = Execution(workspace_id="w-1", state=ExecutionState.CREATED, tags=["t1"], metadata={"run_id": "r-1"})
    e2 = Execution(workspace_id="w-1", state=ExecutionState.QUEUED, tags=["t2"], metadata={"run_id": "r-2"})
    e3 = Execution(workspace_id="w-2", state=ExecutionState.COMPLETED, tags=["t1", "t2"], metadata={"run_id": "r-1"})
    
    repository.create(e1)
    repository.create(e2)
    repository.create(e3)
    
    # List filtering
    w1_list = repository.list(workspace_id="w-1")
    assert len(w1_list) == 2
    
    created_list = repository.list(state=ExecutionState.CREATED)
    assert len(created_list) == 1
    assert created_list[0].id == e1.id

    # Search filtering
    res = repository.search({"tag": "t1"})
    assert len(res) == 2
    
    res = repository.search({"metadata_key": "run_id", "metadata_value": "r-1"})
    assert len(res) == 2
    
    res = repository.search({"workspace_id": "w-1", "state": ExecutionState.QUEUED})
    assert len(res) == 1
    assert res[0].id == e2.id


# ======================================================================
# Phase 3: Scheduler Tests
# ======================================================================

@pytest.mark.asyncio
async def test_execution_scheduler_priority_queue(scheduler, repository, event_bus) -> None:
    """Verifies priority queue fetching order and cancel operations."""
    e1 = Execution(priority=2, tags=["p2"])
    e2 = Execution(priority=10, tags=["p10"])
    e3 = Execution(priority=5, tags=["p5"])
    
    # Persist initially
    repository.create(e1)
    repository.create(e2)
    repository.create(e3)
    
    # Enqueue them
    await scheduler.enqueue(e1)
    await scheduler.enqueue(e2)
    await scheduler.enqueue(e3)
    
    # Dequeue next: should retrieve the highest priority (e2)
    next_task = scheduler.dequeue_next()
    assert next_task is not None
    assert next_task.id == e2.id
    
    # Cancel task e3
    await scheduler.cancel(e3.id)
    cancelled_task = repository.get_by_id(e3.id)
    assert cancelled_task.state == ExecutionState.CANCELLED
    
    # Dequeue next again: should retrieve e1 (since e3 is cancelled, and e2 is not dequeued out of SQLite yet,
    # wait: dequeue_next doesn't update the state to Running/Planning automatically, but let's see. If we transition e2 to running,
    # then it is no longer Queued).
    # Transition e2 to running:
    e2.state = ExecutionState.RUNNING
    repository.update(e2)
    
    next_task2 = scheduler.dequeue_next()
    assert next_task2 is not None
    assert next_task2.id == e1.id


# ======================================================================
# Phase 4: Service and Manager Tests
# ======================================================================

@pytest.mark.asyncio
async def test_execution_service_and_events(service, event_bus) -> None:
    """Verifies service operations emit corresponding events to the EventBus."""
    events_received = []
    
    def on_event(topic, event):
        events_received.append((topic, event))
        
    event_bus.subscribe("execution.#", on_event)
    
    # Create
    exec_data = {"workspace_id": "w-1", "priority": 3}
    created = await service.create_execution(exec_data)
    assert created.state == ExecutionState.CREATED
    
    # Wait for async event dispatch
    await asyncio.sleep(0.05)
    assert len(events_received) == 1
    assert events_received[0][0] == "execution.created"
    
    # Transition
    await service.transition_state(created.id, ExecutionState.RUNNING)
    await asyncio.sleep(0.05)
    assert len(events_received) == 2
    assert events_received[1][0] == "execution.started"
    
    # Add progress
    await service.add_progress(created.id, "Initialized subtasks", 50.0)
    await asyncio.sleep(0.05)
    assert len(events_received) == 3
    assert events_received[2][0] == "execution.progress"
    assert events_received[2][1]["progress_update"]["message"] == "Initialized subtasks"


@pytest.mark.asyncio
async def test_execution_manager_operations(manager, service) -> None:
    """Verifies manager methods for pause, resume, cancel, complete."""
    created = await manager.create_execution({"workspace_id": "w-1"})
    
    # Schedule
    scheduled = await manager.schedule_execution(created.id)
    assert scheduled.state == ExecutionState.QUEUED
    
    # Transition to planning and then pause
    await service.transition_state(created.id, ExecutionState.PLANNING)
    paused = await manager.pause_execution(created.id)
    assert paused.state == ExecutionState.PAUSED
    
    # Resume
    resumed = await manager.resume_execution(created.id)
    assert resumed.state == ExecutionState.QUEUED
    
    # Transition to running
    await service.transition_state(created.id, ExecutionState.RUNNING)
    
    # Complete
    completed = await manager.complete_execution(created.id, success=True)
    assert completed.state == ExecutionState.COMPLETED
    assert completed.completed_at is not None


# ======================================================================
# Setup REST App fixture
# ======================================================================

@pytest.fixture
def rest_app(tmp_path) -> Generator[FastAPI, None, None]:
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
    yield app


# ======================================================================
# Phase 5: REST API Endpoint Tests
# ======================================================================

def test_execution_rest_endpoints(rest_app) -> None:
    """Verifies POST, GET, PATCH, and DELETE REST endpoints for execution resources."""
    with TestClient(rest_app) as client:
        # 1. Create execution
        response = client.post(
            "/api/v1/executions",
            json={
                "priority": 5,
                "timeout": 120.0,
                "tags": ["rest", "api"],
                "metadata": {"test": "rest"}
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        exec_id = data["id"]
        assert data["priority"] == 5
        assert data["timeout"] == 120.0
        assert "rest" in data["tags"]
        assert data["state"] == "Created"
        
        # 2. Get execution details
        response = client.get(f"/api/v1/executions/{exec_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == exec_id
        
        # 3. Patch execution (state transition & priority)
        response = client.patch(
            f"/api/v1/executions/{exec_id}",
            json={
                "state": "Queued",
                "priority": 8,
                "tags": ["rest", "api", "patched"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        patched_data = response.json()
        assert patched_data["state"] == "Queued"
        assert patched_data["priority"] == 8
        assert "patched" in patched_data["tags"]
        
        # 4. List executions
        response = client.get("/api/v1/executions?state=Queued")
        assert response.status_code == status.HTTP_200_OK
        results = response.json()
        assert len(results) >= 1
        assert results[0]["id"] == exec_id
        
        # 5. Delete execution
        response = client.delete(f"/api/v1/executions/{exec_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 6. Verify deleted (GET returns 404)
        response = client.get(f"/api/v1/executions/{exec_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["code"] == "EXECUTION_NOT_FOUND"


# ======================================================================
# Phase 6: WebSocket Notifications Bridge Tests
# ======================================================================

def test_execution_websocket_integration(rest_app) -> None:
    """Verifies WebSocket clients receive execution lifecycle event notifications."""
    with TestClient(rest_app) as client:
        # Create execution via REST to get ID
        res_create = client.post("/api/v1/executions", json={"priority": 1})
        exec_id = res_create.json()["id"]
        
        # Connect to WebSocket
        with client.websocket_connect("/ws?clientId=client-ws") as ws:
            # Subscribe to execution topic wildcard
            ws.send_json({
                "type": "subscribe",
                "id": "sub-exec",
                "payload": {"topic": "execution.#"}
            })
            resp = ws.receive_json()
            assert resp["type"] == "subscribe.ack"
            
            # Now trigger a state transition via REST PATCH (should emit event to bus, then bridge to ws)
            res_patch = client.patch(
                f"/api/v1/executions/{exec_id}",
                json={"state": "Queued"}
            )
            assert res_patch.status_code == status.HTTP_200_OK
            
            # Receive event on WebSocket
            event_msg = ws.receive_json()
            assert event_msg["type"] == "execution.queued"
            assert event_msg["payload"]["id"] == exec_id
            assert event_msg["payload"]["state"] == "Queued"


def test_execution_state_machine_self_transition() -> None:
    """Verifies that transitioning to the same state is a no-op."""
    exec_obj = Execution(state=ExecutionState.CREATED)
    ExecutionStateMachine.transition(exec_obj, ExecutionState.CREATED)
    assert exec_obj.state == ExecutionState.CREATED


def test_execution_validation_errors() -> None:
    """Tests all edge-case failures for ExecutionValidation."""
    exec_obj = Execution()
    
    # 1. Invalid UUID format for correlation_id
    exec_obj.correlation_id = "invalid-corr-id"
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.correlation_id = "4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5"
    
    # 2. Priority type check
    exec_obj.priority = "high"
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.priority = 1
    
    # 3. Retry policy bounds
    exec_obj.retry_policy.backoff_factor = 0.5
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.retry_policy.backoff_factor = 2.0
    
    exec_obj.retry_policy.retry_count = -1
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.retry_policy.retry_count = 0
    
    # 4. Environment variables invalid types
    exec_obj.environment_variables = {123: "val"}
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
        
    exec_obj.environment_variables = {"key": 123}
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.environment_variables = {}
    
    # 5. Metadata keys invalid types
    exec_obj.metadata = {123: "val"}
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.metadata = {}
    
    # 6. Tags invalid types
    exec_obj.tags = [123]
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_create(exec_obj)
    exec_obj.tags = []
    
    # 7. Helper metadata schema validation
    ExecutionValidation.validate_metadata_schema({"timeout": 120.0}, {"timeout": float})
    with pytest.raises(ExecutionValidationError):
        ExecutionValidation.validate_metadata_schema({"timeout": "120"}, {"timeout": float})


def test_repository_edge_cases(repository) -> None:
    """Verifies repository behavior under various edge cases and error states."""
    # 1. Connection not open check
    from unittest.mock import patch, MagicMock
    with patch.object(repository.storage, "connection", None):
        with pytest.raises(ExecutionError):
            repository.create(Execution())
            
    # 2. Update non-existent execution
    with pytest.raises(ExecutionNotFoundError):
        repository.update(Execution(id="00000000-0000-0000-0000-000000000000"))

    # 3. SQLite transaction exceptions (e.g. database locked / rollbacks)
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("Write lock / constraint fail")
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    with patch.object(repository, "_get_connection", return_value=mock_conn):
        with pytest.raises(ExecutionError) as exc_info:
            repository.create(Execution())
        assert "Failed to persist execution" in str(exc_info.value)
        
        with pytest.raises(ExecutionError) as exc_info:
            repository.update(Execution())
        assert "Failed to update execution" in str(exc_info.value)

        with pytest.raises(ExecutionError) as exc_info:
            repository.delete("some-id")
        assert "Failed to delete execution" in str(exc_info.value)

        with pytest.raises(ExecutionError) as exc_info:
            repository.save_event("some-id", "event-id", "some-topic", {})
        assert "Failed to record execution event" in str(exc_info.value)


@pytest.mark.asyncio
async def test_scheduler_cancel_nonexistent(scheduler) -> None:
    """Ensures scheduler cancel raises ExecutionNotFoundError for invalid IDs."""
    with pytest.raises(ExecutionNotFoundError):
        await scheduler.cancel("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_service_restricted_updates(service) -> None:
    """Ensures service state updates can only be executed via state transitions."""
    exec_obj = await service.create_execution({"priority": 1})
    with pytest.raises(ValueError):
        await service.update_execution(exec_obj.id, {"state": ExecutionState.RUNNING})


@pytest.mark.asyncio
async def test_manager_resume_validation(manager, service) -> None:
    """Ensures manager resume raises an error for non-paused executions."""
    exec_obj = await manager.create_execution({"priority": 1})
    with pytest.raises(ExecutionError):
        await manager.resume_execution(exec_obj.id)


def test_rest_api_search_and_edge_cases(rest_app) -> None:
    """Tests the REST search API endpoint and query parameters mapping."""
    with TestClient(rest_app) as client:
        # Create execution
        corr_id = "11111111-2222-3333-4444-555555555555"
        res = client.post(
            "/api/v1/executions",
            json={
                "correlation_id": corr_id,
                "priority": 1,
                "tags": ["test-search"],
                "metadata": {"custom_key": "custom_val"}
            }
        )
        assert res.status_code == status.HTTP_201_CREATED
        
        # 1. Search by exact correlation ID (matching UUID format)
        res_search = client.get(f"/api/v1/executions?search={corr_id}")
        assert res_search.status_code == status.HTTP_200_OK
        results = res_search.json()
        assert len(results) == 1
        assert results[0]["correlation_id"] == corr_id
        
        # 2. Search by tag
        res_tag = client.get("/api/v1/executions?search=test-search")
        assert res_tag.status_code == status.HTTP_200_OK
        assert len(res_tag.json()) == 1

        # 3. Patch with scheduled_at timestamp
        now_str = datetime.now(timezone.utc).isoformat()
        res_patch = client.patch(
            f"/api/v1/executions/{results[0]['id']}",
            json={"scheduled_at": now_str}
        )
        assert res_patch.status_code == status.HTTP_200_OK
        assert res_patch.json()["scheduled_at"] is not None


def test_db_json_parse_errors(repository) -> None:
    """Ensures repository parses corrupted JSON rows gracefully with default values."""
    conn = repository._get_connection()
    cursor = conn.cursor()
    exec_id = "99999999-9999-9999-9999-999999999999"
    cursor.execute(
        """
        INSERT INTO executions (
            id, correlation_id, state, priority, timeout,
            environment_variables_json, retry_policy_json, tags_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (exec_id, "88888888-8888-8888-8888-888888888888", "Created", 1, 100.0, "{invalid_json}", "{invalid_json}", "{invalid_json}")
    )
    conn.commit()
    
    loaded = repository.get_by_id(exec_id)
    assert loaded is not None
    assert loaded.environment_variables == {}
    assert loaded.tags == []
    assert loaded.retry_policy.max_retries == 3

