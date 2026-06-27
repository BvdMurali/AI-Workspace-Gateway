"""
AI Workspace Gateway - Resource Validation
Provides validation rules for resource initialization and updates.
"""

import uuid
from apps.gateway.core.resource.models import Resource
from apps.gateway.core.resource.exceptions import ResourceValidationError


class ResourceValidation:
    """Validator class to check constraints and schemas on resources."""

    @classmethod
    def validate_create(cls, resource: Resource) -> None:
        """Validates resource object parameters on creation."""
        # 1. Verify UUID formatting for id, workspace_id, project_id, and parent_id
        try:
            uuid.UUID(resource.id)
        except ValueError:
            raise ResourceValidationError(f"Resource ID '{resource.id}' is not a valid UUID.")

        try:
            uuid.UUID(resource.workspace_id)
        except ValueError:
            raise ResourceValidationError(f"Workspace ID '{resource.workspace_id}' is not a valid UUID.")

        if resource.project_id:
            try:
                uuid.UUID(resource.project_id)
            except ValueError:
                raise ResourceValidationError(f"Project ID '{resource.project_id}' is not a valid UUID.")

        if resource.parent_id:
            try:
                uuid.UUID(resource.parent_id)
            except ValueError:
                raise ResourceValidationError(f"Parent ID '{resource.parent_id}' is not a valid UUID.")

        # 2. Verify name
        if not resource.name or not resource.name.strip():
            raise ResourceValidationError("Resource name cannot be empty.")
        if len(resource.name) > 255:
            raise ResourceValidationError("Resource name cannot exceed 255 characters.")

        # 3. Verify type
        if not resource.type or not resource.type.strip():
            raise ResourceValidationError("Resource type cannot be empty.")

        # 4. Verify metadata is a dictionary
        if not isinstance(resource.metadata, dict):
            raise ResourceValidationError("Resource metadata must be a dictionary.")

        # 5. Verify tags
        if not isinstance(resource.tags, list):
            raise ResourceValidationError("Tags must be a list.")
        for tag in resource.tags:
            if not isinstance(tag, str):
                raise ResourceValidationError("Tags list must contain only strings.")
