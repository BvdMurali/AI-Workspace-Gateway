"""
AI Workspace Gateway - Execution Service
Implements core business logic for the Execution Framework.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from apps.gateway.events.bus import EventBus
from apps.gateway.core.execution.models import Execution, ExecutionState
from apps.gateway.core.execution.repository import ExecutionRepository
from apps.gateway.core.execution.state_machine import ExecutionStateMachine
from apps.gateway.core.execution.validation import ExecutionValidation
from apps.gateway.core.execution.exceptions import ExecutionNotFoundError
from apps.gateway.core.execution.events import (
    publish_execution_event,
    STATE_TO_TOPIC,
    TOPIC_CREATED,
    TOPIC_PROGRESS
)


class ExecutionService:
    """Contains business logic for managing execution contexts, states, and event notifications."""

    def __init__(self, repository: ExecutionRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def create_execution(self, execution_data: Dict[str, Any]) -> Execution:
        """Creates, validates, and persists a new execution context."""
        execution = Execution.model_validate(execution_data)
        
        # Validate initial creation parameters
        ExecutionValidation.validate_create(execution)
        
        # Persist to SQLite
        self.repository.create(execution)
        
        # Record and publish creation event
        event_id = str(uuid.uuid4())
        payload = execution.model_dump(mode="json")
        self.repository.save_event(execution.id, event_id, TOPIC_CREATED, payload)
        
        await publish_execution_event(self.event_bus, TOPIC_CREATED, execution)
        return execution

    async def get_execution(self, execution_id: str) -> Execution:
        """Retrieves an execution by ID or raises ExecutionNotFoundError."""
        execution = self.repository.get_by_id(execution_id)
        if not execution:
            raise ExecutionNotFoundError(execution_id)
        return execution

    async def update_execution(self, execution_id: str, updates: Dict[str, Any]) -> Execution:
        """Updates specific fields (non-state) of an execution."""
        execution = await self.get_execution(execution_id)
        
        # Restrict direct state updates via update_execution; state changes must go through transition_state
        if "state" in updates:
            target_state = updates["state"]
            if isinstance(target_state, str):
                target_state = ExecutionState(target_state)
            if target_state != execution.state:
                raise ValueError("State transitions must use transition_state() method.")

        # Apply updates
        for field in ["priority", "timeout", "owner", "environment_variables", "metadata", "tags", "scheduled_at"]:
            if field in updates:
                setattr(execution, field, updates[field])

        # Validate
        # Temporary model validation
        updated_model = Execution.model_validate(execution.model_dump())
        # We check timeout and priority constraints
        if updated_model.timeout <= 0:
            raise ValueError("Timeout must be greater than 0.")

        # Persist
        self.repository.update(updated_model)
        
        # Publish progress/update event
        event_id = str(uuid.uuid4())
        payload = updated_model.model_dump(mode="json")
        self.repository.save_event(updated_model.id, event_id, TOPIC_PROGRESS, payload)
        await publish_execution_event(self.event_bus, TOPIC_PROGRESS, updated_model)
        
        return updated_model

    async def transition_state(
        self,
        execution_id: str,
        target_state: ExecutionState,
        extra_payload: Optional[Dict[str, Any]] = None
    ) -> Execution:
        """Performs validated state transition and emits the mapped lifecycle event."""
        execution = await self.get_execution(execution_id)
        
        # Apply and validate transition
        ExecutionStateMachine.transition(execution, target_state)
        
        # Persist
        self.repository.update(execution)
        
        # Emit appropriate event based on state
        topic = STATE_TO_TOPIC.get(target_state, TOPIC_PROGRESS)
        event_id = str(uuid.uuid4())
        payload = execution.model_dump(mode="json")
        if extra_payload:
            payload.update(extra_payload)
            
        self.repository.save_event(execution.id, event_id, topic, payload)
        await publish_execution_event(self.event_bus, topic, execution, extra_payload)
        
        return execution

    async def delete_execution(self, execution_id: str) -> bool:
        """Deletes execution history and contexts from DB."""
        return self.repository.delete(execution_id)

    async def list_executions(
        self,
        state: Optional[ExecutionState] = None,
        workspace_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Execution]:
        """Lists executions using optional filters and pagination."""
        return self.repository.list(state=state, workspace_id=workspace_id, limit=limit, offset=offset)

    async def search_executions(
        self,
        query_params: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[Execution]:
        """Searches executions matching query parameters."""
        return self.repository.search(query_params=query_params, limit=limit, offset=offset)

    async def add_progress(self, execution_id: str, message: str, percent: float = 0.0) -> Execution:
        """Appends progress logs to execution metadata and emits a progress event."""
        execution = await self.get_execution(execution_id)
        
        # Append progress data in metadata
        progress_info = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "message": message,
            "percent": percent
        }
        
        metadata = dict(execution.metadata)
        progress_list = metadata.get("progress_history", [])
        progress_list.append(progress_info)
        metadata["progress_history"] = progress_list
        metadata["last_progress_message"] = message
        metadata["percent_complete"] = percent
        
        execution.metadata = metadata
        execution.updated_at = datetime.now(timezone.utc)
        
        self.repository.update(execution)
        
        # Publish progress event with extra progress details
        event_id = str(uuid.uuid4())
        payload = execution.model_dump(mode="json")
        self.repository.save_event(execution.id, event_id, TOPIC_PROGRESS, payload)
        
        await publish_execution_event(
            self.event_bus,
            TOPIC_PROGRESS,
            execution,
            extra_payload={"progress_update": progress_info}
        )
        return execution
