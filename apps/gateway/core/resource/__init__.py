"""
AI Workspace Gateway - Resource Domain
"""

from apps.gateway.core.resource.models import Resource, ResourceType
from apps.gateway.core.resource.exceptions import (
    ResourceError,
    ResourceNotFoundError,
    ResourceValidationError,
)
from apps.gateway.core.resource.validation import ResourceValidation
from apps.gateway.core.resource.events import (
    publish_resource_event,
    TOPIC_RESOURCE_CREATED,
    TOPIC_RESOURCE_UPDATED,
    TOPIC_RESOURCE_DELETED,
)
from apps.gateway.core.resource.repository import ResourceRepository
from apps.gateway.core.resource.service import ResourceService
from apps.gateway.core.resource.manager import ResourceManager
