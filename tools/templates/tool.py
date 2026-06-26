"""
AI Workspace Gateway - Tool Interface Template
Defines the base classes for custom agent executable actions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ToolContext:
    """Provides access to isolated host adapters within the tool runtime sandbox."""
    def __init__(self, workspace_id: str, logger: Any):
        self.workspace_id = workspace_id
        self.logger = logger

class AbstractTool(ABC):
    """
    Core abstract tool contract.
    All execution tools (filesystem, docker, etc.) must inherit from this class.
    """

    @abstractmethod
    def validate_arguments(self, args: Dict[str, Any]) -> bool:
        """
        Validate incoming arguments against the schema parameters.
        Must return False if validation fails instead of executing actions.
        """
        pass

    @abstractmethod
    async def execute(
        self, 
        args: Dict[str, Any], 
        context: ToolContext
    ) -> Dict[str, Any]:
        """
        Run the tool action payload.
        All execution exceptions must be captured and converted to ToolError instances.
        """
        pass
