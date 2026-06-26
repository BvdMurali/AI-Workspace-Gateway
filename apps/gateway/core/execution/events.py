"""
AI Workspace Gateway - Execution Events
Defines execution lifecycle event topics and event dispatching helpers.
"""

from typing import Any, Dict, Optional
from apps.gateway.events.bus import EventBus
from apps.gateway.core.execution.models import Execution, ExecutionState


# Event topics mapping to execution lifecycle
TOPIC_CREATED = "execution.created"
TOPIC_QUEUED = "execution.queued"
TOPIC_STARTED = "execution.started"
TOPIC_PROGRESS = "execution.progress"
TOPIC_WAITING_APPROVAL = "execution.waiting_approval"
TOPIC_PAUSED = "execution.paused"
TOPIC_COMPLETED = "execution.completed"
TOPIC_FAILED = "execution.failed"
TOPIC_CANCELLED = "execution.cancelled"
TOPIC_TIMEOUT = "execution.timeout"


STATE_TO_TOPIC = {
    ExecutionState.CREATED: TOPIC_CREATED,
    ExecutionState.QUEUED: TOPIC_QUEUED,
    ExecutionState.PLANNING: TOPIC_PROGRESS,  # Planning counts as progress/started
    ExecutionState.RUNNING: TOPIC_STARTED,
    ExecutionState.WAITING_APPROVAL: TOPIC_WAITING_APPROVAL,
    ExecutionState.PAUSED: TOPIC_PAUSED,
    ExecutionState.COMPLETED: TOPIC_COMPLETED,
    ExecutionState.FAILED: TOPIC_FAILED,
    ExecutionState.CANCELLED: TOPIC_CANCELLED,
    ExecutionState.TIMED_OUT: TOPIC_TIMEOUT,
}


async def publish_execution_event(
    event_bus: EventBus,
    event_type: str,
    execution: Execution,
    extra_payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Standard event dispatcher to serialize and publish an execution event
    to the central Event Bus.
    """
    # Use mode="json" to serialize datetime, UUID and Enums properly
    payload = execution.model_dump(mode="json")
    
    if extra_payload:
        payload.update(extra_payload)
        
    await event_bus.publish(event_type, payload)
