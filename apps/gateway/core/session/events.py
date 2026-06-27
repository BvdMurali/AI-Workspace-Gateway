"""
AI Workspace Gateway - Session Events
Defines session lifecycle event topics and event dispatching helpers.
"""

from typing import Any, Dict, Optional
from apps.gateway.events.bus import EventBus
from apps.gateway.core.session.models import Session

TOPIC_SESSION_STARTED = "session.started"
TOPIC_SESSION_UPDATED = "session.updated"
TOPIC_SESSION_ENDED = "session.ended"


async def publish_session_event(
    event_bus: EventBus,
    event_type: str,
    session: Session,
    extra_payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Standard event dispatcher to serialize and publish a session event
    to the central Event Bus.
    """
    payload = session.model_dump(mode="json")
    if extra_payload:
        payload.update(extra_payload)
    await event_bus.publish(event_type, payload)
