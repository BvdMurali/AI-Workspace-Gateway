"""
AI Workspace Gateway - Execution Domain Models
Defines the core models and data schemas for Gateway executions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict


class ExecutionState(str, Enum):
    """Enumeration of all valid execution states."""
    CREATED = "Created"
    QUEUED = "Queued"
    PLANNING = "Planning"
    RUNNING = "Running"
    WAITING_APPROVAL = "WaitingApproval"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    TIMED_OUT = "TimedOut"


class RetryPolicy(BaseModel):
    """Defines retry behaviors and metadata for executions."""
    model_config = ConfigDict(extra="allow")

    max_retries: int = Field(default=3, ge=0)
    backoff_factor: float = Field(default=2.0, ge=1.0)
    retry_count: int = Field(default=0, ge=0)
    last_error: Optional[str] = None


class Execution(BaseModel):
    """
    Standard model representing a Gateway Execution context.
    Designed to be extensible.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: Optional[str] = None
    provider_id: Optional[str] = None
    tool_id: Optional[str] = None
    state: ExecutionState = Field(default=ExecutionState.CREATED)
    priority: int = Field(default=0)
    timeout: float = Field(default=300.0, gt=0.0)  # in seconds, default 5 mins
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    owner: Optional[str] = None
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
