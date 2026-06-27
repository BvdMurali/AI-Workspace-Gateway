"""
AI Workspace Gateway - REST API Integration Tests
"""

from typing import Generator
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from apps.gateway.api.app import create_app
from apps.gateway.bootstrap.lifecycle import Lifecycle


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


def test_workspaces_rest_endpoints(rest_app) -> None:
    """Verifies POST, GET, PATCH, and DELETE REST endpoints for workspaces."""
    with TestClient(rest_app) as client:
        # 1. Create workspace
        res = client.post(
            "/api/v1/workspaces",
            json={
                "name": "Integration Workspace",
                "config": {"theme": "dark"}
            }
        )
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        w_id = data["id"]
        assert data["name"] == "Integration Workspace"
        assert data["config"] == {"theme": "dark"}

        # 2. Get workspace
        res_get = client.get(f"/api/v1/workspaces/{w_id}")
        assert res_get.status_code == status.HTTP_200_OK
        assert res_get.json()["id"] == w_id

        # 3. Patch workspace
        res_patch = client.patch(
            f"/api/v1/workspaces/{w_id}",
            json={
                "name": "Integration Workspace Updated",
                "config": {"theme": "light"}
            }
        )
        assert res_patch.status_code == status.HTTP_200_OK
        assert res_patch.json()["name"] == "Integration Workspace Updated"
        assert res_patch.json()["config"] == {"theme": "light"}

        # 4. List workspaces
        res_list = client.get("/api/v1/workspaces")
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.json()) >= 1
        assert any(w["id"] == w_id for w in res_list.json())

        # 5. Delete workspace
        res_del = client.delete(f"/api/v1/workspaces/{w_id}")
        assert res_del.status_code == status.HTTP_204_NO_CONTENT

        # 6. Verify deleted
        res_verify = client.get(f"/api/v1/workspaces/{w_id}")
        assert res_verify.status_code == status.HTTP_404_NOT_FOUND


def test_projects_rest_endpoints(rest_app, tmp_path) -> None:
    """Verifies POST and GET REST endpoints for projects."""
    with TestClient(rest_app) as client:
        # Create workspace first
        res_w = client.post("/api/v1/workspaces", json={"name": "WS for Project"})
        w_id = res_w.json()["id"]

        # Create project
        proj_dir = tmp_path / "test-project"
        proj_dir.mkdir()
        
        # We can optionally create .git inside it
        (proj_dir / ".git").mkdir()
        (proj_dir / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

        res_p = client.post(
            "/api/v1/projects",
            json={
                "workspace_id": w_id,
                "name": "My REST Project",
                "root_path": str(proj_dir),
                "tags": ["integration", "test"],
                "environment_variables": {"DEBUG": "true"}
            }
        )
        assert res_p.status_code == status.HTTP_201_CREATED
        p_data = res_p.json()
        assert p_data["name"] == "My REST Project"
        assert p_data["repository_metadata"]["branch"] == "main"

        # List projects
        res_list = client.get(f"/api/v1/projects?workspace_id={w_id}")
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.json()) == 1
        assert res_list.json()[0]["id"] == p_data["id"]


def test_resources_rest_endpoints(rest_app) -> None:
    """Verifies GET REST endpoint for resources and query/search parameters."""
    with TestClient(rest_app) as client:
        # Create workspace
        res_w = client.post("/api/v1/workspaces", json={"name": "WS for Resources"})
        w_id = res_w.json()["id"]

        # Listing workspaces automatically registered a resource representing the workspace
        res_list = client.get(f"/api/v1/resources?workspace_id={w_id}")
        assert res_list.status_code == status.HTTP_200_OK
        # Should contain 1 resource (the Workspace resource registered by manager)
        assert len(res_list.json()) == 1
        assert res_list.json()[0]["type"] == "Workspace"
        assert res_list.json()[0]["name"] == "WS for Resources"

        # Try searching by query parameter
        res_search = client.get(f"/api/v1/resources?search=WS")
        assert res_search.status_code == status.HTTP_200_OK
        assert len(res_search.json()) >= 1


@pytest.mark.asyncio
async def test_sessions_rest_endpoints(rest_app) -> None:
    """Verifies GET REST endpoint for sessions."""
    with TestClient(rest_app) as client:
        # Create workspace
        res_w = client.post("/api/v1/workspaces", json={"name": "WS for Sessions"})
        w_id = res_w.json()["id"]

        # Let's start a session directly via the lifecycle's SessionManager
        lifecycle = rest_app.state.lifecycle
        from apps.gateway.core.session import SessionManager as SM
        sm = lifecycle.container.resolve(SM)
        await sm.start_session({
            "workspace_id": w_id,
            "name": "Integration Session"
        })

        # List sessions
        res_list = client.get(f"/api/v1/sessions?workspace_id={w_id}")
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.json()) == 1
        assert res_list.json()[0]["name"] == "Integration Session"
        assert res_list.json()[0]["state"] == "Active"
