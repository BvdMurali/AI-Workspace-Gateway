"""
AI Workspace Gateway - Project Domain Unit Tests
"""

import asyncio
import os
from typing import Generator
import pytest
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.repository import WorkspaceRepository
from apps.gateway.core.project.models import Project
from apps.gateway.core.project.validation import ProjectValidation
from apps.gateway.core.project.discovery import RepositoryDiscoveryService
from apps.gateway.core.project.repository import ProjectRepository
from apps.gateway.core.project.service import ProjectService
from apps.gateway.core.project.manager import ProjectManager
from apps.gateway.core.project.exceptions import (
    ProjectError,
    ProjectNotFoundError,
    ProjectValidationError
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
def workspace(temp_storage) -> Workspace:
    repo = WorkspaceRepository(temp_storage)
    w = Workspace(name="Project Test Workspace")
    return repo.create(w)


@pytest.fixture
def project_repo(temp_storage) -> ProjectRepository:
    return ProjectRepository(temp_storage)


@pytest.fixture
def project_service(project_repo, event_bus) -> ProjectService:
    return ProjectService(project_repo, event_bus)


@pytest.fixture
def discovery_service() -> RepositoryDiscoveryService:
    return RepositoryDiscoveryService()


@pytest.fixture
def resource_repo(temp_storage) -> ResourceRepository:
    return ResourceRepository(temp_storage)


@pytest.fixture
def resource_service(resource_repo, event_bus) -> ResourceService:
    return ResourceService(resource_repo, event_bus)


@pytest.fixture
def manager(project_service, discovery_service, resource_service) -> ProjectManager:
    return ProjectManager(project_service, discovery_service, resource_service)


def test_project_validation() -> None:
    """Verifies project validation rules."""
    p = Project(
        workspace_id="4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5",
        name="Valid Project",
        root_path="/path/to/project"
    )
    ProjectValidation.validate_create(p)

    # Empty name
    p.name = ""
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.name = "a" * 256
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.name = "Project"

    # Empty root path
    p.root_path = " "
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.root_path = "/path"

    # Invalid UUIDs
    p.workspace_id = "not-a-uuid"
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.workspace_id = "4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5"

    p.id = "not-a-uuid"
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.id = "4f8a96d1-f8a4-4a4f-9e7f-1d4e48b11ff5"

    # Env variables validation
    p.environment_variables = {123: "val"}
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.environment_variables = {"k": 123}
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.environment_variables = {}

    # Tags validation
    p.tags = [123]
    with pytest.raises(ProjectValidationError):
        ProjectValidation.validate_create(p)
    p.tags = []


def test_repository_discovery(tmp_path, discovery_service) -> None:
    """Verifies git repository discovery parsesconfig/HEAD files properly."""
    # 1. Create a dummy git repo directory
    repo_dir = tmp_path / "my-repo"
    git_dir = repo_dir / ".git"
    git_dir.mkdir(parents=True)
    
    # Write HEAD
    (git_dir / "HEAD").write_text("ref: refs/heads/feature/sprint-4\n", encoding="utf-8")
    
    # Write config
    git_config = """[core]
	repositoryformatversion = 0
	filemode = true
[remote "origin"]
	url = git@github.com:test/my-repo.git
	fetch = +refs/heads/*:refs/remotes/origin/*
"""
    (git_config_file := git_dir / "config").write_text(git_config, encoding="utf-8")

    # Run discovery on the parent tmp_path
    repos = discovery_service.discover_repositories(str(tmp_path))
    assert len(repos) == 1
    
    repo = repos[0]
    assert repo["name"] == "my-repo"
    assert repo["root_path"] == str(repo_dir)
    assert repo["branch"] == "feature/sprint-4"
    assert repo["remote_url"] == "git@github.com:test/my-repo.git"
    assert "Sprint 4" in repo["status_summary"] or "sprint-4" in repo["status_summary"]

    # Detached HEAD check
    (git_dir / "HEAD").write_text("a1b2c3d4e5f6\n", encoding="utf-8")
    repos = discovery_service.discover_repositories(str(tmp_path))
    assert repos[0]["branch"] == "a1b2c3d4"


def test_project_repository_crud(project_repo, workspace) -> None:
    """Verifies CRUD operations on ProjectRepository."""
    p = Project(
        workspace_id=workspace.id,
        name="Project CRUD",
        root_path="/workspace/project-crud",
        tags=["development"],
        environment_variables={"ENV": "dev"},
        repository_metadata={"branch": "main"}
    )

    # 1. CREATE
    saved = project_repo.create(p)
    assert saved.id == p.id
    assert saved.name == "Project CRUD"
    assert saved.tags == ["development"]
    assert saved.environment_variables == {"ENV": "dev"}
    assert saved.repository_metadata == {"branch": "main"}

    # Create under non-existent workspace
    with pytest.raises(Exception):
        project_repo.create(Project(workspace_id="00000000-0000-0000-0000-000000000000", name="Project B", root_path="/path"))

    # 2. READ
    loaded = project_repo.get_by_id(p.id)
    assert loaded is not None
    assert loaded.workspace_id == workspace.id
    assert loaded.name == p.name

    assert project_repo.get_by_id("00000000-0000-0000-0000-000000000000") is None

    # 3. UPDATE
    loaded.name = "Project CRUD Updated"
    loaded.provider_preference = "claude"
    updated = project_repo.update(loaded)
    assert updated.name == "Project CRUD Updated"
    assert updated.provider_preference == "claude"

    # Update non-existent
    with pytest.raises(ProjectNotFoundError):
        project_repo.update(Project(id="00000000-0000-0000-0000-000000000000", workspace_id=workspace.id, name="None", root_path="/path"))

    # 4. DELETE
    assert project_repo.delete(p.id) is True
    assert project_repo.get_by_id(p.id) is None
    assert project_repo.delete(p.id) is False


def test_project_repository_list(project_repo, workspace) -> None:
    """Verifies listing and filtering."""
    p1 = Project(workspace_id=workspace.id, name="Project A", root_path="/a")
    p2 = Project(workspace_id=workspace.id, name="Project B", root_path="/b")
    project_repo.create(p1)
    project_repo.create(p2)

    lst = project_repo.list(workspace_id=workspace.id)
    assert len(lst) >= 2
    names = [p.name for p in lst]
    assert "Project A" in names
    assert "Project B" in names


@pytest.mark.asyncio
async def test_project_service_events(project_service, workspace, event_bus) -> None:
    """Verifies service operations emit project events."""
    events_received = []

    def on_event(topic, event):
        events_received.append((topic, event))

    event_bus.subscribe("project.#", on_event)

    # Create
    created = await project_service.create_project({
        "workspace_id": workspace.id,
        "name": "Service Project",
        "root_path": "/path/service"
    })
    await asyncio.sleep(0.01)
    assert len(events_received) == 1
    assert events_received[0][0] == "project.created"

    # Update
    await project_service.update_project(created.id, {"name": "Service Project Updated"})
    await asyncio.sleep(0.01)
    assert len(events_received) == 2
    assert events_received[1][0] == "project.updated"

    # Delete
    await project_service.delete_project(created.id)
    await asyncio.sleep(0.01)
    assert len(events_received) == 3
    assert events_received[2][0] == "project.deleted"


@pytest.mark.asyncio
async def test_project_manager_resource_registration(tmp_path, manager, workspace, resource_service) -> None:
    """Verifies that project creation automatically triggers repo discovery and registers Project/Git resources."""
    # 1. Create a dummy git repo directory
    repo_dir = tmp_path / "project-repo"
    git_dir = repo_dir / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    
    # 2. Create project using manager
    project = await manager.create_project({
        "workspace_id": workspace.id,
        "name": "Manager Project",
        "root_path": str(repo_dir)
    })

    # Check project has repository metadata populated
    assert project.repository_metadata != {}
    assert project.repository_metadata["branch"] == "main"

    # Check that it got registered in resources (both Project and Git Repository)
    proj_resources = await resource_service.list_resources(project_id=project.id, type="Project")
    assert len(proj_resources) == 1
    assert proj_resources[0].name == "Manager Project"

    git_resources = await resource_service.list_resources(project_id=project.id, type="Git Repository")
    assert len(git_resources) == 1
    assert git_resources[0].name == "project-repo"
    assert git_resources[0].metadata["branch"] == "main"
