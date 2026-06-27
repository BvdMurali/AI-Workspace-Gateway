"""
AI Workspace Gateway - Workspace Domain Models
Defines the core models and data schemas for Gateway workspaces.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict


class Workspace(BaseModel):
    """
    Standard model representing a Gateway Workspace context.
    Designed to be extensible.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
