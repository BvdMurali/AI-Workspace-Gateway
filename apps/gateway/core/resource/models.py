"""
AI Workspace Gateway - Resource Domain Models
Defines the core models and data schemas for Gateway resources.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict


class ResourceType(str, Enum):
    """Supported default resource types in the AI Workspace Gateway."""
    WORKSPACE = "Workspace"
    PROJECT = "Project"
    GIT_REPOSITORY = "Git Repository"
    FOLDER = "Folder"
    FILE = "File"
    TERMINAL_SESSION = "Terminal Session"
    DOCKER_CONTAINER = "Docker Container"
    ENVIRONMENT = "Environment"
    CREDENTIAL = "Credential"
    EXECUTION = "Execution"


class Resource(BaseModel):
    """
    Standard model representing a generic Gateway Resource.
    Designed to be extensible.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = Field(...)
    project_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(...)  # ResourceType value or custom string
    path: Optional[str] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
