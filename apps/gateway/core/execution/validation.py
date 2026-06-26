"""
AI Workspace Gateway - Execution Validation
Provides validation rules for execution initialization and updates.
"""

from typing import Any, Dict
import uuid

from apps.gateway.core.execution.models import Execution, ExecutionState
from apps.gateway.core.execution.exceptions import ExecutionValidationError


class ExecutionValidation:
    """Validator class to check constraints and schemas on executions."""

    @classmethod
    def validate_create(cls, execution: Execution) -> None:
        """Validates execution object parameters on creation."""
        # 1. Verify UUID formatting for id and correlation_id if provided
        try:
            uuid.UUID(execution.id)
        except ValueError:
            raise ExecutionValidationError(f"Execution ID '{execution.id}' is not a valid UUID.")

        try:
            uuid.UUID(execution.correlation_id)
        except ValueError:
            raise ExecutionValidationError(f"Correlation ID '{execution.correlation_id}' is not a valid UUID.")

        # 2. State must be CREATED initially
        if execution.state != ExecutionState.CREATED:
            raise ExecutionValidationError(
                f"New execution must start in state '{ExecutionState.CREATED.value}', "
                f"received '{execution.state.value}'."
            )

        # 3. Verify priority
        if not isinstance(execution.priority, int):
            raise ExecutionValidationError(
                f"Priority must be an integer, received {type(execution.priority).__name__}."
            )

        # 4. Verify timeout
        if execution.timeout <= 0:
            raise ExecutionValidationError(
                f"Timeout must be a positive number greater than 0, received {execution.timeout}."
            )

        # 5. Verify retry policy
        retry_policy = execution.retry_policy
        if retry_policy.max_retries < 0:
            raise ExecutionValidationError(
                f"Retry policy max_retries must be non-negative, received {retry_policy.max_retries}."
            )
        if retry_policy.backoff_factor < 1.0:
            raise ExecutionValidationError(
                f"Retry policy backoff_factor must be >= 1.0, received {retry_policy.backoff_factor}."
            )
        if retry_policy.retry_count < 0:
            raise ExecutionValidationError(
                f"Retry policy retry_count must be non-negative, received {retry_policy.retry_count}."
            )

        # 6. Verify environment variables keys and values
        if not isinstance(execution.environment_variables, dict):
            raise ExecutionValidationError("Environment variables must be a dictionary.")
        for k, v in execution.environment_variables.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ExecutionValidationError("Environment variables keys and values must be strings.")

        # 7. Verify metadata keys
        if not isinstance(execution.metadata, dict):
            raise ExecutionValidationError("Metadata must be a dictionary.")
        for k in execution.metadata.keys():
            if not isinstance(k, str):
                raise ExecutionValidationError("Metadata keys must be strings.")

        # 8. Verify tags
        if not isinstance(execution.tags, list):
            raise ExecutionValidationError("Tags must be a list.")
        for tag in execution.tags:
            if not isinstance(tag, str):
                raise ExecutionValidationError("Tags list must contain only strings.")

    @classmethod
    def validate_metadata_schema(cls, metadata: Dict[str, Any], schema: Dict[str, type]) -> None:
        """Helper to validate metadata against a basic type schema."""
        for key, expected_type in schema.items():
            if key in metadata:
                val = metadata[key]
                if not isinstance(val, expected_type):
                    raise ExecutionValidationError(
                        f"Metadata key '{key}' expects type {expected_type.__name__}, "
                        f"received {type(val).__name__}."
                    )
