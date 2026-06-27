"""
AI Workspace Gateway - Project Validation
Provides validation rules for project initialization and updates.
"""

import uuid
from apps.gateway.core.project.models import Project
from apps.gateway.core.project.exceptions import ProjectValidationError


class ProjectValidation:
    """Validator class to check constraints and schemas on projects."""

    @classmethod
    def validate_create(cls, project: Project) -> None:
        """Validates project object parameters on creation."""
        # 1. Verify UUID formatting for id and workspace_id
        try:
            uuid.UUID(project.id)
        except ValueError:
            raise ProjectValidationError(f"Project ID '{project.id}' is not a valid UUID.")

        try:
            uuid.UUID(project.workspace_id)
        except ValueError:
            raise ProjectValidationError(f"Workspace ID '{project.workspace_id}' is not a valid UUID.")

        # 2. Verify name
        if not project.name or not project.name.strip():
            raise ProjectValidationError("Project name cannot be empty.")
        if len(project.name) > 255:
            raise ProjectValidationError("Project name cannot exceed 255 characters.")

        # 3. Verify root path
        if not project.root_path or not project.root_path.strip():
            raise ProjectValidationError("Project root path cannot be empty.")

        # 4. Verify repository_metadata is a dictionary
        if not isinstance(project.repository_metadata, dict):
            raise ProjectValidationError("Project repository_metadata must be a dictionary.")

        # 5. Verify environment variables keys and values
        if not isinstance(project.environment_variables, dict):
            raise ProjectValidationError("Environment variables must be a dictionary.")
        for k, v in project.environment_variables.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ProjectValidationError("Environment variables keys and values must be strings.")

        # 6. Verify tags
        if not isinstance(project.tags, list):
            raise ProjectValidationError("Tags must be a list.")
        for tag in project.tags:
            if not isinstance(tag, str):
                raise ProjectValidationError("Tags list must contain only strings.")
