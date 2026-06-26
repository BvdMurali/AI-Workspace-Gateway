"""
AI Workspace Gateway - Execution Manager
Coordinates executions across the service and scheduler boundaries.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from apps.gateway.core.execution.models import Execution, ExecutionState
from apps.gateway.core.execution.service import ExecutionService
from apps.gateway.core.execution.scheduler import ExecutionScheduler
from apps.gateway.core.execution.exceptions import ExecutionError


class ExecutionManager:
    """High-level orchestration manager for executions."""

    def __init__(self, service: ExecutionService, scheduler: ExecutionScheduler) -> None:
        self.service = service
        self.scheduler = scheduler

    async def create_execution(self, execution_data: Dict[str, Any]) -> Execution:
        """Creates a new execution context."""
        return await self.service.create_execution(execution_data)

    async def schedule_execution(self, execution_id: str, scheduled_at: Optional[datetime] = None) -> Execution:
        """Schedules an execution to be run immediately or at a specific future timestamp."""
        execution = await self.service.get_execution(execution_id)
        if scheduled_at:
            # Enforce UTC timezone
            execution.scheduled_at = scheduled_at.replace(tzinfo=timezone.utc) if scheduled_at.tzinfo is None else scheduled_at
            
        await self.scheduler.enqueue(execution)
        # Reload to return the fresh scheduled/queued state
        return await self.service.get_execution(execution_id)

    async def cancel_execution(self, execution_id: str) -> Execution:
        """Cancels a scheduled, queued, or active execution."""
        await self.scheduler.cancel(execution_id)
        return await self.service.get_execution(execution_id)

    async def pause_execution(self, execution_id: str) -> Execution:
        """Pauses a planning or running execution."""
        return await self.service.transition_state(execution_id, ExecutionState.PAUSED)

    async def resume_execution(self, execution_id: str) -> Execution:
        """Resumes a paused execution, re-queueing it in the scheduler."""
        execution = await self.service.get_execution(execution_id)
        if execution.state != ExecutionState.PAUSED:
            raise ExecutionError(f"Cannot resume execution in state '{execution.state.value}'. Only 'Paused' executions can be resumed.")
            
        # Re-enqueue the execution
        await self.scheduler.enqueue(execution)
        return await self.service.get_execution(execution_id)

    async def complete_execution(
        self,
        execution_id: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Execution:
        """Completes an execution, marking it as Completed or Failed."""
        execution = await self.service.get_execution(execution_id)
        
        extra_payload = {}
        if success:
            target_state = ExecutionState.COMPLETED
        else:
            target_state = ExecutionState.FAILED
            # Update retry policy error
            execution.retry_policy.last_error = error_message
            self.service.repository.update(execution)
            if error_message:
                extra_payload["error"] = error_message
                
        return await self.service.transition_state(execution_id, target_state, extra_payload=extra_payload)
