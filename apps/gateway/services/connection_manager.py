"""
AI Workspace Gateway - Connection Manager
Tracks, monitors, and cleans up active client connections.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, Optional, Set
from fastapi import WebSocket


class Connection:
    """Represents a single active client connection."""

    def __init__(
        self,
        connection_id: str,
        client_id: str,
        websocket: WebSocket,
        transport: str = "websocket"
    ) -> None:
        self.connection_id = connection_id
        self.client_id = client_id
        self.websocket = websocket
        self.connected_since = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
        self.subscriptions: Set[str] = set()
        self.transport = transport
        self.state = "connected"

    def to_dict(self) -> dict:
        """Serializes connection metadata for inspection."""
        return {
            "connection_id": self.connection_id,
            "client_id": self.client_id,
            "connected_since": self.connected_since.isoformat().replace("+00:00", "Z"),
            "last_heartbeat": self.last_heartbeat.isoformat().replace("+00:00", "Z"),
            "subscriptions": list(self.subscriptions),
            "transport": self.transport,
            "state": self.state
        }


class ConnectionManager:
    """Manages active connection pools and handles automatic stale connection cleanups."""

    def __init__(
        self,
        idle_timeout_seconds: float = 60.0,
        cleanup_interval_seconds: float = 10.0,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.idle_timeout = idle_timeout_seconds
        self.cleanup_interval = cleanup_interval_seconds
        self.logger = logger or logging.getLogger("gateway")
        
        self.active_connections: Dict[str, Connection] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    def connect(self, connection_id: str, client_id: str, websocket: WebSocket) -> Connection:
        """Registers a newly established client connection."""
        connection = Connection(connection_id, client_id, websocket)
        self.active_connections[connection_id] = connection
        self.logger.info(
            f"Registered connection '{connection_id}' for client '{client_id}'. "
            f"Total active: {len(self.active_connections)}"
        )
        return connection

    async def disconnect(self, connection_id: str) -> Optional[Connection]:
        """Deregisters and closes a client connection."""
        connection = self.active_connections.pop(connection_id, None)
        if connection:
            connection.state = "disconnected"
            self.logger.info(
                f"Deregistered connection '{connection_id}' for client '{connection.client_id}'. "
                f"Remaining active: {len(self.active_connections)}"
            )
            # Try to close websocket if still open
            try:
                await connection.websocket.close()
            except Exception:
                pass
        return connection

    def update_heartbeat(self, connection_id: str) -> bool:
        """Updates the last heartbeat timestamp of a connection."""
        connection = self.active_connections.get(connection_id)
        if connection:
            connection.last_heartbeat = datetime.now(timezone.utc)
            self.logger.debug(f"Updated heartbeat timestamp for connection '{connection_id}'")
            return True
        return False

    def subscribe(self, connection_id: str, topic_pattern: str) -> bool:
        """Registers a subscription pattern to a connection."""
        connection = self.active_connections.get(connection_id)
        if connection:
            connection.subscriptions.add(topic_pattern)
            self.logger.info(f"Connection '{connection_id}' subscribed to topic: '{topic_pattern}'")
            return True
        return False

    def unsubscribe(self, connection_id: str, topic_pattern: str) -> bool:
        """Deregisters a subscription pattern from a connection."""
        connection = self.active_connections.get(connection_id)
        if connection:
            connection.subscriptions.discard(topic_pattern)
            self.logger.info(f"Connection '{connection_id}' unsubscribed from topic: '{topic_pattern}'")
            return True
        return False

    async def start(self) -> None:
        """Starts the connection cleanup background worker loop."""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("ConnectionManager stale connection cleanup worker started.")

    async def stop(self) -> None:
        """Gracefully stops the cleanup loop and terminates all connections."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            
        # Close all active connections
        connections_to_close = list(self.active_connections.keys())
        for conn_id in connections_to_close:
            await self.disconnect(conn_id)
        
        self.logger.info("ConnectionManager stale connection cleanup worker shut down.")

    async def _cleanup_loop(self) -> None:
        """Loop that checks for and purges stale connections."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._check_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in stale connection cleanup loop: {e}", exc_info=True)

    async def _check_stale_connections(self) -> None:
        """Identifies and purges connections that exceeded the idle timeout threshold."""
        now = datetime.now(timezone.utc)
        stale_ids = []
        
        for conn_id, conn in self.active_connections.items():
            elapsed = (now - conn.last_heartbeat).total_seconds()
            if elapsed > self.idle_timeout:
                self.logger.warning(
                    f"Connection '{conn_id}' of client '{conn.client_id}' is stale "
                    f"(last heartbeat {elapsed:.1f}s ago, limit: {self.idle_timeout}s). Enqueueing cleanup."
                )
                stale_ids.append(conn_id)

        for conn_id in stale_ids:
            await self.disconnect(conn_id)
