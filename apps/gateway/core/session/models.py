"""
AI Workspace Gateway - Session Domain Models
Defines the core models and data schemas for Gateway sessions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict


class SessionState(str, Enum):
    """Enumeration of all valid session states."""
    ACTIVE = "Active"
    IDLE = "Idle"
    ENDED = "Ended"


class Session(BaseModel):
    """
    Standard model representing a Gateway Session context.
    Tracks connected clients, last activity, and related execution/workspace/project context.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = Field(...)
    project_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    connected_clients: List[str] = Field(default_factory=list)
    current_execution_id: Optional[str] = None
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state: SessionState = Field(default=SessionState.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
