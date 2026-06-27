"""
AI Workspace Gateway - Project Events
Defines project lifecycle event topics and event dispatching helpers.
"""

from typing import Any, Dict, Optional
from apps.gateway.events.bus import EventBus
from apps.gateway.core.project.models import Project

TOPIC_PROJECT_CREATED = "project.created"
TOPIC_PROJECT_UPDATED = "project.updated"
TOPIC_PROJECT_DELETED = "project.deleted"


async def publish_project_event(
    event_bus: EventBus,
    event_type: str,
    project: Project,
    extra_payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Standard event dispatcher to serialize and publish a project event
    to the central Event Bus.
    """
    payload = project.model_dump(mode="json")
    if extra_payload:
        payload.update(extra_payload)
    await event_bus.publish(event_type, payload)
