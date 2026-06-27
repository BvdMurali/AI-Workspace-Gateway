"""
AI Workspace Gateway - Resource Events
Defines resource lifecycle event topics and event dispatching helpers.
"""

from typing import Any, Dict, Optional
from apps.gateway.events.bus import EventBus
from apps.gateway.core.resource.models import Resource

TOPIC_RESOURCE_CREATED = "resource.created"
TOPIC_RESOURCE_UPDATED = "resource.updated"
TOPIC_RESOURCE_DELETED = "resource.deleted"


async def publish_resource_event(
    event_bus: EventBus,
    event_type: str,
    resource: Resource,
    extra_payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Standard event dispatcher to serialize and publish a resource event
    to the central Event Bus.
    """
    payload = resource.model_dump(mode="json")
    if extra_payload:
        payload.update(extra_payload)
    await event_bus.publish(event_type, payload)
