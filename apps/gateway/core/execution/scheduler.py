"""
AI Workspace Gateway - Execution Scheduler
Provides infrastructure for priority queuing and scheduling of executions.
"""

from datetime import datetime, timezone
import uuid
from typing import Optional

from apps.gateway.events.bus import EventBus
from apps.gateway.core.execution.models import Execution, ExecutionState
from apps.gateway.core.execution.repository import ExecutionRepository
from apps.gateway.core.execution.state_machine import ExecutionStateMachine
from apps.gateway.core.execution.events import publish_execution_event, TOPIC_QUEUED, TOPIC_CANCELLED


class ExecutionScheduler:
    """Manages the scheduling, queueing, and cancellation of executions."""

    def __init__(self, repository: ExecutionRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def enqueue(self, execution: Execution) -> None:
        """Enqueues an execution for future processing."""
        # Update state via state machine
        ExecutionStateMachine.transition(execution, ExecutionState.QUEUED)
        
        # If scheduled_at is not set, default to now (run as soon as possible)
        if not execution.scheduled_at:
            execution.scheduled_at = datetime.now(timezone.utc)
            
        # Persist state change
        self.repository.update(execution)
        
        # Save event to SQLite and publish to EventBus
        event_id = str(uuid.uuid4())
        payload = execution.model_dump(mode="json")
        self.repository.save_event(execution.id, event_id, TOPIC_QUEUED, payload)
        
        await publish_execution_event(self.event_bus, TOPIC_QUEUED, execution)

    async def cancel(self, execution_id: str) -> None:
        """Cancels a scheduled or queued execution."""
        execution = self.repository.get_by_id(execution_id)
        if not execution:
            from apps.gateway.core.execution.exceptions import ExecutionNotFoundError
            raise ExecutionNotFoundError(execution_id)
            
        # Update state via state machine
        ExecutionStateMachine.transition(execution, ExecutionState.CANCELLED)
        
        # Persist state change
        self.repository.update(execution)
        
        # Save event to SQLite and publish to EventBus
        event_id = str(uuid.uuid4())
        payload = execution.model_dump(mode="json")
        self.repository.save_event(execution.id, event_id, TOPIC_CANCELLED, payload)
        
        await publish_execution_event(self.event_bus, TOPIC_CANCELLED, execution)

    def dequeue_next(self) -> Optional[Execution]:
        """Retrieves the next queued execution based on priority and scheduling timestamp."""
        now = datetime.now(timezone.utc)
        return self.repository.get_next_queued(now)
