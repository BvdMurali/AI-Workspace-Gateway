"""
AI Workspace Gateway - Event Bus Unit Tests
"""

import pytest
from apps.gateway.events.bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_pub_sub() -> None:
    """Verifies basic subscription and event publishing."""
    bus = EventBus()
    received_events = []

    def on_event(topic: str, event: Any) -> None:
        received_events.append((topic, event))

    bus.subscribe("test.topic", on_event)
    await bus.publish("test.topic", "hello_world")

    assert len(received_events) == 1
    assert received_events[0] == ("test.topic", "hello_world")


@pytest.mark.asyncio
async def test_event_bus_async_callback() -> None:
    """Verifies that asynchronous callbacks are awaited successfully."""
    bus = EventBus()
    received = []

    async def on_event_async(topic: str, event: Any) -> None:
        received.append((topic, event))

    bus.subscribe("test.topic", on_event_async)
    await bus.publish("test.topic", "async_payload")

    assert len(received) == 1
    assert received[0] == ("test.topic", "async_payload")


@pytest.mark.asyncio
async def test_event_bus_unsubscribe() -> None:
    """Verifies that unsubscribing stops callback invocation."""
    bus = EventBus()
    received = []

    def handler(topic: str, event: Any) -> None:
        received.append(event)

    bus.subscribe("test.topic", handler)
    await bus.publish("test.topic", 1)
    
    bus.unsubscribe("test.topic", handler)
    await bus.publish("test.topic", 2)

    assert received == [1]


@pytest.mark.asyncio
async def test_event_bus_wildcards() -> None:
    """Verifies wildcard matching patterns like * and #."""
    bus = EventBus()
    wildcard_single = []  # session.*
    wildcard_multi = []   # session.#
    wildcard_all = []     # *

    bus.subscribe("session.*", lambda t, e: wildcard_single.append((t, e)))
    bus.subscribe("session.#", lambda t, e: wildcard_multi.append((t, e)))
    bus.subscribe("*", lambda t, e: wildcard_all.append((t, e)))

    # 1. Publish to single sub-segment
    await bus.publish("session.started", "event_1")
    # 2. Publish to nested sub-segments
    await bus.publish("session.message.received", "event_2")
    # 3. Publish to unrelated topic
    await bus.publish("system.boot", "event_3")

    # session.* should match session.started but not session.message.received or system.boot
    assert len(wildcard_single) == 1
    assert wildcard_single[0][0] == "session.started"

    # session.# should match both session.started and session.message.received
    assert len(wildcard_multi) == 2
    assert wildcard_multi[0][0] == "session.started"
    assert wildcard_multi[1][0] == "session.message.received"

    # * should match everything
    assert len(wildcard_all) == 3


@pytest.mark.asyncio
async def test_event_bus_resilience() -> None:
    """Verifies that an exception in one handler does not halt event delivery to others."""
    bus = EventBus()
    delivered = []

    def failing_handler(topic: str, event: Any) -> None:
        raise RuntimeError("Failing subscriber")

    def working_handler(topic: str, event: Any) -> None:
        delivered.append(event)

    bus.subscribe("test", failing_handler)
    bus.subscribe("test", working_handler)

    # Should not raise exception
    await bus.publish("test", "payload")
    assert delivered == ["payload"]
