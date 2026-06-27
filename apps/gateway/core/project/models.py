"""
AI Workspace Gateway - Project Domain Models
Defines the core models and data schemas for Gateway projects.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict


class Project(BaseModel):
    """
    Standard model representing a Gateway Project context.
    Designed to be extensible.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = Field(...)
    name: str = Field(..., min_length=1, max_length=255)
    root_path: str = Field(..., min_length=1)
    repository_metadata: Dict[str, Any] = Field(default_factory=dict)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    provider_preference: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
