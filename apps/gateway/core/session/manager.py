"""
AI Workspace Gateway - Session Manager
Coordinates active developer sessions and client connectivity state.
"""

from typing import Any, Dict, List, Optional
from apps.gateway.core.session.models import Session
from apps.gateway.core.session.service import SessionService


class SessionManager:
    """High-level orchestration manager for Sessions."""

    def __init__(self, service: SessionService) -> None:
        self.service = service

    async def start_session(self, session_data: Dict[str, Any]) -> Session:
        """Starts a new session."""
        return await self.service.create_session(session_data)

    async def register_client(self, session_id: str, client_id: str) -> Session:
        """Registers a client connection to a session."""
        return await self.service.add_client(session_id, client_id)

    async def deregister_client(self, session_id: str, client_id: str) -> Session:
        """Deregisters a client connection from a session."""
        return await self.service.remove_client(session_id, client_id)

    async def keep_alive(self, session_id: str) -> Session:
        """Keeps session alive by updating last activity timestamp."""
        return await self.service.update_activity(session_id)

    async def end_session(self, session_id: str) -> bool:
        """Gracefully ends and deletes a session."""
        return await self.service.delete_session(session_id)
