"""
AI Workspace Gateway - Session Service
Implements core business logic for managing sessions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from apps.gateway.events.bus import EventBus
from apps.gateway.core.session.models import Session, SessionState
from apps.gateway.core.session.repository import SessionRepository
from apps.gateway.core.session.validation import SessionValidation
from apps.gateway.core.session.exceptions import SessionNotFoundError
from apps.gateway.core.session.events import (
    publish_session_event,
    TOPIC_SESSION_STARTED,
    TOPIC_SESSION_UPDATED,
    TOPIC_SESSION_ENDED
)


class SessionService:
    """Contains business logic for managing session contexts and lifecycle events."""

    def __init__(self, repository: SessionRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def create_session(self, session_data: Dict[str, Any]) -> Session:
        """Creates, validates, and persists a new session."""
        session = Session.model_validate(session_data)
        
        # Validate
        SessionValidation.validate_create(session)
        
        # Persist
        self.repository.create(session)
        
        # Publish event
        await publish_session_event(self.event_bus, TOPIC_SESSION_STARTED, session)
        return session

    async def get_session(self, session_id: str) -> Session:
        """Retrieves a session by ID or raises SessionNotFoundError."""
        session = self.repository.get_by_id(session_id)
        if not session:
            raise SessionNotFoundError(session_id)
        return session

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Session:
        """Updates specific fields of a session."""
        session = await self.get_session(session_id)
        
        # Apply updates
        for field in ["workspace_id", "project_id", "name", "connected_clients", "current_execution_id", "state"]:
            if field in updates:
                setattr(session, field, updates[field])
                
        if "last_activity" in updates:
            session.last_activity = updates["last_activity"]
        else:
            session.last_activity = datetime.now(timezone.utc)

        # Validate
        SessionValidation.validate_create(session)
        
        # Persist
        self.repository.update(session)
        
        # Publish event
        await publish_session_event(self.event_bus, TOPIC_SESSION_UPDATED, session)
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Deletes session from database and publishes ended event."""
        session = self.repository.get_by_id(session_id)
        if not session:
            return False
            
        # Transition state to Ended before deletion to represent correctly in the event
        session.state = SessionState.ENDED
        session.last_activity = datetime.now(timezone.utc)
        
        deleted = self.repository.delete(session_id)
        if deleted:
            await publish_session_event(self.event_bus, TOPIC_SESSION_ENDED, session)
        return deleted

    async def list_sessions(
        self,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        state: Optional[SessionState] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Session]:
        """Lists sessions with optional filtering and pagination."""
        return self.repository.list(workspace_id=workspace_id, project_id=project_id, state=state, limit=limit, offset=offset)

    async def add_client(self, session_id: str, client_id: str) -> Session:
        """Adds a connected client to the session."""
        session = await self.get_session(session_id)
        if client_id not in session.connected_clients:
            clients = list(session.connected_clients)
            clients.append(client_id)
            return await self.update_session(session_id, {
                "connected_clients": clients,
                "state": SessionState.ACTIVE
            })
        return session

    async def remove_client(self, session_id: str, client_id: str) -> Session:
        """Removes a connected client from the session."""
        session = await self.get_session(session_id)
        if client_id in session.connected_clients:
            clients = [c for c in session.connected_clients if c != client_id]
            # If no clients are connected, optionally transition to Idle
            target_state = SessionState.IDLE if not clients else session.state
            return await self.update_session(session_id, {
                "connected_clients": clients,
                "state": target_state
            })
        return session

    async def update_activity(self, session_id: str) -> Session:
        """Updates last activity timestamp."""
        return await self.update_session(session_id, {})
