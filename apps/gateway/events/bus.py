"""
AI Workspace Gateway - Event Bus
Provides publish-subscribe event routing with support for topic wildcards.
"""

import asyncio
import logging
import re
from typing import Any, Callable, Dict, Optional, Set, Union


class EventBus:
    """In-memory event bus supporting wildcard subscriptions and asynchronous dispatch."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("gateway")
        # Maps a pattern to a set of subscriber callbacks
        self._subscribers: Dict[str, Set[Callable[[str, Any], Any]]] = {}
        # Caches compiled regex patterns for performance
        self._compiled_patterns: Dict[str, re.Pattern] = {}

    def subscribe(self, pattern: str, callback: Callable[[str, Any], Any]) -> None:
        """Subscribes a callback to a topic pattern."""
        if pattern not in self._subscribers:
            self._subscribers[pattern] = set()
            self._compiled_patterns[pattern] = self._topic_to_regex(pattern)
        self._subscribers[pattern].add(callback)
        self.logger.debug(f"Subscribed callback to pattern: {pattern}")

    def unsubscribe(self, pattern: str, callback: Callable[[str, Any], Any]) -> None:
        """Unsubscribes a callback from a topic pattern."""
        if pattern in self._subscribers:
            self._subscribers[pattern].discard(callback)
            if not self._subscribers[pattern]:
                del self._subscribers[pattern]
                del self._compiled_patterns[pattern]
            self.logger.debug(f"Unsubscribed callback from pattern: {pattern}")

    async def publish(self, topic: str, event: Any) -> None:
        """Publishes an event to a topic, matching wildcard subscribers."""
        self.logger.debug(f"Publishing event to topic '{topic}'")
        tasks = []
        for pattern, callbacks in self._subscribers.items():
            if self._compiled_patterns[pattern].match(topic):
                for callback in callbacks:
                    tasks.append(self._invoke_callback(callback, topic, event))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _invoke_callback(self, callback: Callable[[str, Any], Any], topic: str, event: Any) -> None:
        """Helper to invoke sync or async callbacks safely."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(topic, event)
            else:
                callback(topic, event)
        except Exception as e:
            self.logger.error(
                f"Error in event subscriber callback for topic '{topic}': {e}",
                exc_info=True,
                extra={"topic": topic, "error": str(e)}
            )

    def _topic_to_regex(self, pattern: str) -> re.Pattern:
        """Converts an AMQP-style wildcard pattern into a compiled regex pattern."""
        if pattern == "*":
            return re.compile(r"^.*$")
            
        parts = pattern.split(".")
        regex_parts = []
        for part in parts:
            if part == "*":
                # Matches exactly one segment (containing characters other than dot)
                regex_parts.append(r"[^.]+")
            elif part == "#":
                # Matches zero or more segments
                regex_parts.append(r".*")
            else:
                regex_parts.append(re.escape(part))
                
        regex_str = r"^" + r"\.".join(regex_parts) + r"$"
        # Fix possible double dot matchers caused by '#' mapping
        regex_str = regex_str.replace(r"\..*", r"(\..*)?").replace(r".*\.", r"(.*?\.)?")
        return re.compile(regex_str)

    def shutdown(self) -> None:
        """Cleans up the event bus, clearing subscribers."""
        self.logger.info("Shutting down Event Bus")
        self._subscribers.clear()
        self._compiled_patterns.clear()
