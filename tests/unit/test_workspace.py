"""
AI Workspace Gateway - Workspace Domain Unit Tests
"""

import asyncio
from typing import Generator
import pytest
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.validation import WorkspaceValidation
from apps.gateway.core.workspace.repository import WorkspaceRepository
from apps.gateway.core.workspace.service import WorkspaceService
from apps.gateway.core.workspace.manager import WorkspaceManager
from apps.gateway.core.workspace.exceptions import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError,
    DuplicateWorkspaceNameError
)
from apps.gateway.core.resource.repository import ResourceRepository
from apps.gateway.core.resource.service import ResourceService
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
def resource_repo(temp_storage) -> ResourceRepository:
    return ResourceRepository(temp_storage)


@pytest.fixture
def resource_service(resource_repo, event_bus) -> ResourceService:
    return ResourceService(resource_repo, event_bus)


@pytest.fixture
def repository(temp_storage) -> WorkspaceRepository:
    return WorkspaceRepository(temp_storage)


@pytest.fixture
def service(repository, event_bus) -> WorkspaceService:
    return WorkspaceService(repository, event_bus)


@pytest.fixture
def manager(service, resource_service) -> WorkspaceManager:
    return WorkspaceManager(service, resource_service)


def test_workspace_validation() -> None:
    """Verifies that validation enforces required fields and bounds."""
    w = Workspace(name="Default Workspace")
    WorkspaceValidation.validate_create(w)

    # Empty name
    w.name = ""
    with pytest.raises(WorkspaceValidationError):
        WorkspaceValidation.validate_create(w)
    w.name = "   "
    with pytest.raises(WorkspaceValidationError):
        WorkspaceValidation.validate_create(w)
    w.name = "a" * 256
    with pytest.raises(WorkspaceValidationError):
        WorkspaceValidation.validate_create(w)

    w.name = "Valid Workspace"
    # Invalid ID
    w.id = "not-a-uuid"
    with pytest.raises(WorkspaceValidationError):
        WorkspaceValidation.validate_create(w)
    w.id = "4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5"

    # Invalid config keys
    w.config = {123: "val"}
    with pytest.raises(WorkspaceValidationError):
        WorkspaceValidation.validate_create(w)
    w.config = {}


def test_workspace_repository_crud(repository) -> None:
    """Verifies CREATE, READ, UPDATE, and DELETE operations in SQLite."""
    w = Workspace(name="Repository Workspace", config={"test": True})
    
    # 1. CREATE
    saved = repository.create(w)
    assert saved.id == w.id
    assert saved.name == "Repository Workspace"
    assert saved.config == {"test": True}

    # Duplicate name check
    w_dup = Workspace(name="Repository Workspace")
    with pytest.raises(DuplicateWorkspaceNameError):
        repository.create(w_dup)

    # 2. READ
    loaded = repository.get_by_id(w.id)
    assert loaded is not None
    assert loaded.name == w.name
    assert loaded.config == w.config

    loaded_name = repository.get_by_name(w.name)
    assert loaded_name is not None
    assert loaded_name.id == w.id

    assert repository.get_by_id("00000000-0000-0000-0000-000000000000") is None
    assert repository.get_by_name("Non existent") is None

    # 3. UPDATE
    loaded.name = "Updated Workspace"
    loaded.config = {"test": False, "updated": True}
    updated = repository.update(loaded)
    assert updated.name == "Updated Workspace"
    assert updated.config == {"test": False, "updated": True}

    # Verify duplicate name check on update
    w_another = Workspace(name="Another Workspace")
    repository.create(w_another)
    updated.name = "Another Workspace"
    with pytest.raises(DuplicateWorkspaceNameError):
        repository.update(updated)

    # Update non-existent
    with pytest.raises(WorkspaceNotFoundError):
        repository.update(Workspace(id="00000000-0000-0000-0000-000000000000", name="None"))

    # 4. DELETE
    assert repository.delete(w.id) is True
    assert repository.get_by_id(w.id) is None
    assert repository.delete(w.id) is False


def test_workspace_repository_list(repository) -> None:
    """Verifies listing and pagination."""
    w1 = Workspace(name="Workspace A")
    w2 = Workspace(name="Workspace B")
    repository.create(w1)
    repository.create(w2)

    lst = repository.list(limit=10)
    assert len(lst) >= 2
    names = [w.name for w in lst]
    assert "Workspace A" in names
    assert "Workspace B" in names


@pytest.mark.asyncio
async def test_workspace_service_events(service, event_bus) -> None:
    """Verifies service operations emit corresponding events."""
    events_received = []

    def on_event(topic, event):
        events_received.append((topic, event))

    event_bus.subscribe("workspace.#", on_event)

    # Create
    created = await service.create_workspace({"name": "Service Workspace"})
    await asyncio.sleep(0.01)
    assert len(events_received) == 1
    assert events_received[0][0] == "workspace.created"
    assert events_received[0][1]["name"] == "Service Workspace"

    # Update
    await service.update_workspace(created.id, {"name": "Service Workspace Updated"})
    await asyncio.sleep(0.01)
    assert len(events_received) == 2
    assert events_received[1][0] == "workspace.updated"

    # Delete
    await service.delete_workspace(created.id)
    await asyncio.sleep(0.01)
    assert len(events_received) == 3
    assert events_received[2][0] == "workspace.deleted"


@pytest.mark.asyncio
async def test_workspace_manager_resource_registration(manager, resource_service) -> None:
    """Verifies manager registers and updates workspace resource."""
    created = await manager.create_workspace({"name": "Manager Workspace", "config": {"owner": "admin"}})
    
    # Check that it got registered in resources
    resources = await resource_service.list_resources(workspace_id=created.id, type="Workspace")
    assert len(resources) == 1
    assert resources[0].name == "Manager Workspace"
    assert resources[0].metadata == {"owner": "admin"}

    # Update workspace
    await manager.update_workspace(created.id, {"name": "Manager Workspace Updated", "config": {"owner": "user"}})
    resources_updated = await resource_service.list_resources(workspace_id=created.id, type="Workspace")
    assert len(resources_updated) == 1
    assert resources_updated[0].name == "Manager Workspace Updated"
    assert resources_updated[0].metadata == {"owner": "user"}

    # Delete workspace
    await manager.delete_workspace(created.id)
    # Check that workspace is deleted
    with pytest.raises(WorkspaceNotFoundError):
        await manager.service.get_workspace(created.id)
