# ADR-0004: Event Driven Core

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
Agent workflows, RAG calculations, and streaming updates are asynchronous operations. Coupling modules directly blocks run loops.

## Decision
Decouple gateway modules using a centralized in-process Event Bus. Modules dispatch typed events (e.g., `agent.tool.executed`) and listen to topics without direct service references.

## Consequences
*   **Pros**: Asynchronous processing, low-latency API response loops, easy plugin hook integration.
*   **Cons**: Debugging stack traces is more complex due to event boundaries.

## Alternatives Considered
*   **Synchronous Service Calls**: Rejected due to blocking operations during RAG ingestion.

## Tradeoffs
*   Trading debug tracing simplicity for low-latency concurrency.

## References
*   [EVENT_PROTOCOL.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/sdk/EVENT_PROTOCOL.md)
