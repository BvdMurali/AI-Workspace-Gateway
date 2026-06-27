"""
AI Workspace Gateway - Workspace Events
Defines workspace lifecycle event topics and event dispatching helpers.
"""

from typing import Any, Dict, Optional
from apps.gateway.events.bus import EventBus
from apps.gateway.core.workspace.models import Workspace

TOPIC_WORKSPACE_CREATED = "workspace.created"
TOPIC_WORKSPACE_UPDATED = "workspace.updated"
TOPIC_WORKSPACE_DELETED = "workspace.deleted"


async def publish_workspace_event(
    event_bus: EventBus,
    event_type: str,
    workspace: Workspace,
    extra_payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Standard event dispatcher to serialize and publish a workspace event
    to the central Event Bus.
    """
    payload = workspace.model_dump(mode="json")
    if extra_payload:
        payload.update(extra_payload)
    await event_bus.publish(event_type, payload)
