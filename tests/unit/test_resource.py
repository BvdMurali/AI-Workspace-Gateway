"""
AI Workspace Gateway - Resource Domain Unit Tests
"""

import asyncio
from typing import Generator
import pytest
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.repository import WorkspaceRepository
from apps.gateway.core.project.models import Project
from apps.gateway.core.project.repository import ProjectRepository
from apps.gateway.core.resource.models import Resource, ResourceType
from apps.gateway.core.resource.validation import ResourceValidation
from apps.gateway.core.resource.repository import ResourceRepository
from apps.gateway.core.resource.service import ResourceService
from apps.gateway.core.resource.manager import ResourceManager
from apps.gateway.core.resource.exceptions import (
    ResourceError,
    ResourceNotFoundError,
    ResourceValidationError
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
    w = Workspace(name="Resource Test Workspace")
    return repo.create(w)


@pytest.fixture
def project(temp_storage, workspace) -> Project:
    repo = ProjectRepository(temp_storage)
    p = Project(workspace_id=workspace.id, name="Resource Test Project", root_path="/path")
    return repo.create(p)


@pytest.fixture
def repository(temp_storage) -> ResourceRepository:
    return ResourceRepository(temp_storage)


@pytest.fixture
def service(repository, event_bus) -> ResourceService:
    return ResourceService(repository, event_bus)


@pytest.fixture
def manager(service) -> ResourceManager:
    return ResourceManager(service)


def test_resource_validation() -> None:
    """Verifies resource validation rules."""
    r = Resource(
        workspace_id="4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5",
        name="Valid Resource",
        type="File"
    )
    ResourceValidation.validate_create(r)

    # Empty name
    r.name = ""
    with pytest.raises(ResourceValidationError):
        ResourceValidation.validate_create(r)
    r.name = "Resource"

    # Empty type
    r.type = " "
    with pytest.raises(ResourceValidationError):
        ResourceValidation.validate_create(r)
    r.type = "Workspace"

    # Invalid UUIDs
    r.workspace_id = "not-a-uuid"
    with pytest.raises(ResourceValidationError):
        ResourceValidation.validate_create(r)
    r.workspace_id = "4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5"

    r.project_id = "not-a-uuid"
    with pytest.raises(ResourceValidationError):
        ResourceValidation.validate_create(r)
    r.project_id = None

    r.parent_id = "not-a-uuid"
    with pytest.raises(ResourceValidationError):
        ResourceValidation.validate_create(r)
    r.parent_id = None


def test_resource_repository_crud(repository, workspace, project) -> None:
    """Verifies CRUD operations on ResourceRepository."""
    r = Resource(
        workspace_id=workspace.id,
        project_id=project.id,
        name="File.py",
        type=ResourceType.FILE,
        path="/path/File.py",
        metadata={"size": 1024, "ext": "py"},
        tags=["python", "src"]
    )

    # 1. CREATE
    saved = repository.create(r)
    assert saved.id == r.id
    assert saved.name == "File.py"
    assert saved.metadata == {"size": 1024, "ext": "py"}
    assert saved.tags == ["python", "src"]

    # 2. READ
    loaded = repository.get_by_id(r.id)
    assert loaded is not None
    assert loaded.workspace_id == workspace.id
    assert loaded.project_id == project.id
    assert loaded.name == r.name
    assert loaded.type == r.type
    assert loaded.metadata == r.metadata
    assert loaded.tags == r.tags

    # 3. UPDATE
    loaded.name = "File2.py"
    loaded.metadata["size"] = 2048
    loaded.tags.append("modified")
    updated = repository.update(loaded)
    assert updated.name == "File2.py"
    assert updated.metadata["size"] == 2048
    assert "modified" in updated.tags

    # Update non-existent
    with pytest.raises(ResourceNotFoundError):
        repository.update(Resource(id="00000000-0000-0000-0000-000000000000", workspace_id=workspace.id, name="None", type="File"))

    # 4. DELETE
    assert repository.delete(r.id) is True
    assert repository.get_by_id(r.id) is None
    assert repository.delete(r.id) is False


def test_resource_repository_search_and_filter(repository, workspace, project) -> None:
    """Verifies search, filtering and metadata extraction."""
    r1 = Resource(
        workspace_id=workspace.id,
        project_id=project.id,
        name="Docker Container 1",
        type=ResourceType.DOCKER_CONTAINER,
        metadata={"port": 8080, "image": "nginx"},
        tags=["nginx", "web"]
    )
    r2 = Resource(
        workspace_id=workspace.id,
        project_id=project.id,
        name="Env File",
        type=ResourceType.ENVIRONMENT,
        metadata={"env": "dev"},
        tags=["config"]
    )
    repository.create(r1)
    repository.create(r2)

    # 1. Type filter
    list_type = repository.list(workspace_id=workspace.id, type=ResourceType.ENVIRONMENT)
    assert len(list_type) == 1
    assert list_type[0].name == "Env File"

    # 2. Metadata search (key and value)
    res = repository.search({"workspace_id": workspace.id, "metadata_key": "port", "metadata_value": 8080})
    assert len(res) == 1
    assert res[0].name == "Docker Container 1"

    # 3. Tag search
    res_tag = repository.search({"workspace_id": workspace.id, "tag": "nginx"})
    assert len(res_tag) == 1
    assert res_tag[0].name == "Docker Container 1"

    # 4. Name check (LIKE)
    res_name = repository.search({"workspace_id": workspace.id, "name": "Docker"})
    assert len(res_name) == 1
    assert res_name[0].name == "Docker Container 1"


@pytest.mark.asyncio
async def test_resource_service_events(service, workspace, event_bus) -> None:
    """Verifies service operations emit resource events."""
    events_received = []

    def on_event(topic, event):
        events_received.append((topic, event))

    event_bus.subscribe("resource.#", on_event)

    # Create
    created = await service.create_resource({
        "workspace_id": workspace.id,
        "name": "Resource Service A",
        "type": "File"
    })
    await asyncio.sleep(0.01)
    assert len(events_received) == 1
    assert events_received[0][0] == "resource.created"

    # Update
    await service.update_resource(created.id, {"name": "Resource Service A Updated"})
    await asyncio.sleep(0.01)
    assert len(events_received) == 2
    assert events_received[1][0] == "resource.updated"

    # Delete
    await service.delete_resource(created.id)
    await asyncio.sleep(0.01)
    assert len(events_received) == 3
    assert events_received[2][0] == "resource.deleted"
