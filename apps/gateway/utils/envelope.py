"""
AI Workspace Gateway - Message Envelope
Provides a standardized schema for all WebSocket communications.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict


class MessageEnvelope(BaseModel):
    """
    Standard envelope format for all client-server communication.
    Ensures message structure consistency.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    version: str = "v1"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    correlation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)



def create_error_payload(code: str, message: str, retryable: bool = False) -> Dict[str, Any]:
    """Helper to generate a standardized error payload."""
    return {
        "code": code,
        "message": message,
        "retryable": retryable
    }
