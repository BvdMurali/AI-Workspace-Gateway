"""
AI Workspace Gateway - Execution State Machine
Handles logic for valid transitions between execution states.
"""

from datetime import datetime, timezone
from typing import Dict, Set

from apps.gateway.core.execution.models import Execution, ExecutionState
from apps.gateway.core.execution.exceptions import InvalidStateTransitionError


class ExecutionStateMachine:
    """Manages state transitions and transition validation for executions."""

    # Set of valid state transitions: maps a state to the set of allowed target states
    VALID_TRANSITIONS: Dict[ExecutionState, Set[ExecutionState]] = {
        ExecutionState.CREATED: {
            ExecutionState.QUEUED,
            ExecutionState.PLANNING,
            ExecutionState.RUNNING,
            ExecutionState.CANCELLED,
        },
        ExecutionState.QUEUED: {
            ExecutionState.PLANNING,
            ExecutionState.RUNNING,
            ExecutionState.CANCELLED,
        },
        ExecutionState.PLANNING: {
            ExecutionState.RUNNING,
            ExecutionState.WAITING_APPROVAL,
            ExecutionState.PAUSED,
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
            ExecutionState.TIMED_OUT,
        },
        ExecutionState.RUNNING: {
            ExecutionState.WAITING_APPROVAL,
            ExecutionState.PAUSED,
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
            ExecutionState.TIMED_OUT,
        },
        ExecutionState.WAITING_APPROVAL: {
            ExecutionState.PLANNING,
            ExecutionState.RUNNING,
            ExecutionState.PAUSED,
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
            ExecutionState.TIMED_OUT,
        },
        ExecutionState.PAUSED: {
            ExecutionState.QUEUED,
            ExecutionState.PLANNING,
            ExecutionState.RUNNING,
            ExecutionState.CANCELLED,
        },
        # Terminal states have no outbound transitions
        ExecutionState.COMPLETED: set(),
        ExecutionState.FAILED: set(),
        ExecutionState.CANCELLED: set(),
        ExecutionState.TIMED_OUT: set(),
    }

    @classmethod
    def validate_transition(cls, from_state: ExecutionState, to_state: ExecutionState) -> None:
        """Raises InvalidStateTransitionError if the state transition is invalid."""
        if from_state == to_state:
            return  # Transitioning to the same state is a no-op / valid

        allowed = cls.VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidStateTransitionError(from_state.value, to_state.value)

    @classmethod
    def transition(cls, execution: Execution, target_state: ExecutionState) -> Execution:
        """
        Validates transition and updates execution state, updated_at,
        and completed_at if transitioning to a terminal state.
        """
        cls.validate_transition(execution.state, target_state)
        
        now = datetime.now(timezone.utc)
        execution.state = target_state
        execution.updated_at = now
        
        # If transitioning to a terminal state, record completion time
        if target_state in {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED, ExecutionState.TIMED_OUT}:
            execution.completed_at = now
            
        return execution
