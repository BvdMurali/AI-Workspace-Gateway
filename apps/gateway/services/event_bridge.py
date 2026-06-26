"""
AI Workspace Gateway - Event Bridge
Bridges the internal Event Bus to WebSocket connections based on subscriptions.
"""

import asyncio
import logging
import re
from typing import Any, Dict, Optional
from apps.gateway.events.bus import EventBus
from apps.gateway.services.connection_manager import ConnectionManager
from apps.gateway.utils.envelope import MessageEnvelope


class EventBridge:
    """Listens to the system EventBus and routes matching events to active WebSockets."""

    def __init__(
        self,
        event_bus: EventBus,
        connection_manager: ConnectionManager,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.event_bus = event_bus
        self.connection_manager = connection_manager
        self.logger = logger or logging.getLogger("gateway")
        self._subscribed = False
        
        # Compiled regex cache for client subscription patterns
        self._pattern_cache: Dict[str, re.Pattern] = {}

    def start(self) -> None:
        """Starts bridging events by subscribing to all topics on the EventBus."""
        if self._subscribed:
            return
            
        self.event_bus.subscribe("#", self._handle_event)
        self._subscribed = True
        self.logger.info("EventBridge started. Subscribed to all EventBus topics ('#').")

    def stop(self) -> None:
        """Stops bridging events."""
        if not self._subscribed:
            return
            
        self.event_bus.unsubscribe("#", self._handle_event)
        self._subscribed = False
        self._pattern_cache.clear()
        self.logger.info("EventBridge stopped.")

    async def _handle_event(self, topic: str, event: Any) -> None:
        """Callback invoked whenever the EventBus dispatches an event."""
        # Retrieve all currently active connections
        connections = list(self.connection_manager.active_connections.values())
        if not connections:
            return

        tasks = []
        for conn in connections:
            # Check if this connection is subscribed to this event topic
            subscribed = False
            for pattern in conn.subscriptions:
                if self._matches_pattern(topic, pattern):
                    subscribed = True
                    break
            
            if subscribed:
                # Wrap event in MessageEnvelope and send
                envelope = MessageEnvelope(
                    type=topic,
                    payload=event if isinstance(event, dict) else {"event_data": event}
                )
                tasks.append(self._send_to_connection(conn.connection_id, conn.websocket, envelope))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_connection(self, connection_id: str, websocket: Any, envelope: MessageEnvelope) -> None:
        """Dispatches an envelope JSON payload to a specific WebSocket connection."""
        try:
            await websocket.send_json(envelope.model_dump())
        except Exception as e:
            self.logger.warning(
                f"Failed to route event '{envelope.type}' to connection '{connection_id}': {e}. "
                f"Initiating disconnect."
            )
            # Cleanup broken connection
            await self.connection_manager.disconnect(connection_id)

    def _matches_pattern(self, topic: str, pattern: str) -> bool:
        """Determines if a topic matches an AMQP-style wildcard subscription pattern."""
        if pattern == "#":
            return True
            
        if pattern not in self._pattern_cache:
            self._pattern_cache[pattern] = self._compile_pattern(pattern)
            
        return bool(self._pattern_cache[pattern].match(topic))

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Converts an AMQP wildcard topic pattern into a compiled regex."""
        parts = pattern.split(".")
        regex_parts = []
        for part in parts:
            if part == "*":
                regex_parts.append(r"[^.]+")
            elif part == "#":
                regex_parts.append(r".*")
            else:
                regex_parts.append(re.escape(part))
                
        regex_str = r"^" + r"\.".join(regex_parts) + r"$"
        regex_str = regex_str.replace(r"\..*", r"(\..*)?").replace(r".*\.", r"(.*?\.)?")
        return re.compile(regex_str)
class_name = "EventBridge"
