"""
AI Workspace Gateway - Session Domain Unit Tests
"""

import asyncio
from typing import Generator
import pytest
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.repository import WorkspaceRepository
from apps.gateway.core.project.models import Project
from apps.gateway.core.project.repository import ProjectRepository
from apps.gateway.core.session.models import Session, SessionState
from apps.gateway.core.session.validation import SessionValidation
from apps.gateway.core.session.repository import SessionRepository
from apps.gateway.core.session.service import SessionService
from apps.gateway.core.session.manager import SessionManager
from apps.gateway.core.session.exceptions import (
    SessionError,
    SessionNotFoundError,
    SessionValidationError
)
from apps.gateway.events.bus import EventBus
from apps.gateway.storage.bootstrap import StorageBootstrap


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
def workspace(temp_storage) -> Workspace:
    repo = WorkspaceRepository(temp_storage)
    w = Workspace(name="Session Test Workspace")
    return repo.create(w)


@pytest.fixture
def project(temp_storage, workspace) -> Project:
    repo = ProjectRepository(temp_storage)
    p = Project(workspace_id=workspace.id, name="Session Test Project", root_path="/path")
    return repo.create(p)


@pytest.fixture
def repository(temp_storage) -> SessionRepository:
    return SessionRepository(temp_storage)


@pytest.fixture
def service(repository, event_bus) -> SessionService:
    return SessionService(repository, event_bus)


@pytest.fixture
def manager(service) -> SessionManager:
    return SessionManager(service)


def test_session_validation() -> None:
    """Verifies session validation rules."""
    s = Session(
        workspace_id="4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5",
        name="Valid Session"
    )
    SessionValidation.validate_create(s)

    # Empty name
    s.name = ""
    with pytest.raises(SessionValidationError):
        SessionValidation.validate_create(s)
    s.name = "Session"

    # Invalid UUIDs
    s.workspace_id = "not-a-uuid"
    with pytest.raises(SessionValidationError):
        SessionValidation.validate_create(s)
    s.workspace_id = "4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5"

    s.project_id = "not-a-uuid"
    with pytest.raises(SessionValidationError):
        SessionValidation.validate_create(s)
    s.project_id = None

    s.current_execution_id = "not-a-uuid"
    with pytest.raises(SessionValidationError):
        SessionValidation.validate_create(s)
    s.current_execution_id = None

    # Invalid clients
    s.connected_clients = [123]
    with pytest.raises(SessionValidationError):
        SessionValidation.validate_create(s)
    s.connected_clients = []


def test_session_repository_crud(repository, workspace, project) -> None:
    """Verifies CRUD operations on SessionRepository."""
    s = Session(
        workspace_id=workspace.id,
        project_id=project.id,
        name="Developer Session 1",
        connected_clients=["client-1", "client-2"],
        current_execution_id=None,
        state=SessionState.ACTIVE
    )

    # 1. CREATE
    saved = repository.create(s)
    assert saved.id == s.id
    assert saved.name == "Developer Session 1"
    assert saved.connected_clients == ["client-1", "client-2"]
    assert saved.state == SessionState.ACTIVE

    # 2. READ
    loaded = repository.get_by_id(s.id)
    assert loaded is not None
    assert loaded.workspace_id == workspace.id
    assert loaded.project_id == project.id
    assert loaded.name == s.name
    assert loaded.connected_clients == s.connected_clients
    assert loaded.state == s.state

    # 3. UPDATE
    loaded.name = "Developer Session 1 Updated"
    loaded.connected_clients.append("client-3")
    loaded.state = SessionState.IDLE
    updated = repository.update(loaded)
    assert updated.name == "Developer Session 1 Updated"
    assert updated.connected_clients == ["client-1", "client-2", "client-3"]
    assert updated.state == SessionState.IDLE

    # Update non-existent
    with pytest.raises(SessionNotFoundError):
        repository.update(Session(id="00000000-0000-0000-0000-000000000000", workspace_id=workspace.id, name="None"))

    # 4. DELETE
    assert repository.delete(s.id) is True
    assert repository.get_by_id(s.id) is None
    assert repository.delete(s.id) is False


def test_session_repository_list(repository, workspace, project) -> None:
    """Verifies listing and filtering of sessions."""
    s1 = Session(workspace_id=workspace.id, project_id=project.id, name="Session A", state=SessionState.ACTIVE)
    s2 = Session(workspace_id=workspace.id, project_id=project.id, name="Session B", state=SessionState.IDLE)
    repository.create(s1)
    repository.create(s2)

    lst = repository.list(workspace_id=workspace.id, state=SessionState.ACTIVE)
    assert len(lst) >= 1
    assert any(s.name == "Session A" for s in lst)
    assert not any(s.name == "Session B" for s in lst)


@pytest.mark.asyncio
async def test_session_service_events(service, workspace, event_bus) -> None:
    """Verifies service operations emit session events."""
    events_received = []

    def on_event(topic, event):
        events_received.append((topic, event))

    event_bus.subscribe("session.#", on_event)

    # Start/Create Session -> session.started
    created = await service.create_session({
        "workspace_id": workspace.id,
        "name": "Service Session"
    })
    await asyncio.sleep(0.01)
    assert len(events_received) == 1
    assert events_received[0][0] == "session.started"

    # Update Session -> session.updated
    await service.update_session(created.id, {"state": SessionState.IDLE})
    await asyncio.sleep(0.01)
    assert len(events_received) == 2
    assert events_received[1][0] == "session.updated"

    # Delete/End Session -> session.ended
    await service.delete_session(created.id)
    await asyncio.sleep(0.01)
    assert len(events_received) == 3
    assert events_received[2][0] == "session.ended"


@pytest.mark.asyncio
async def test_session_manager_client_registration(manager, workspace) -> None:
    """Verifies manager registers and keep-alives client connections."""
    s = await manager.start_session({
        "workspace_id": workspace.id,
        "name": "Manager Session"
    })

    # Register client
    updated = await manager.register_client(s.id, "client-x")
    assert "client-x" in updated.connected_clients
    assert updated.state == SessionState.ACTIVE

    # Keep alive
    orig_activity = updated.last_activity
    await asyncio.sleep(0.01)
    alive = await manager.keep_alive(s.id)
    assert alive.last_activity > orig_activity

    # Deregister client
    final = await manager.deregister_client(s.id, "client-x")
    assert "client-x" not in final.connected_clients
    # No clients connected, so it transitions to Idle
    assert final.state == SessionState.IDLE

    # End session
    assert await manager.end_session(s.id) is True
