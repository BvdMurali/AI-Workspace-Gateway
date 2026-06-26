# ADR-0001: Local First Architecture

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
AI orchestrators traditionally route user prompts, vector chunks, and configuration details to cloud databases. This creates security liabilities, lock-in dependencies, and egress fees.

## Decision
The core execution engine, vector database indices, and conversation histories must execute and persist locally on the user's host workstation. Cloud endpoints are accessed only via direct client-side provider APIs.

## Consequences
*   **Pros**: Absolute privacy, zero-latency database checks, full offline capability when routed to local model wrappers (like Ollama).
*   **Cons**: Decentralized device synchronization requires complex Peer-to-Peer protocols (CRDTs).

## Alternatives Considered
*   **Centralized Cloud Sync**: Rejected due to privacy violations.
*   **Self-hosted Server**: Kept as an optional deployment tunnel target, but not as the baseline system architecture.

## Tradeoffs
*   Trading synchronization simplicity for user privacy and security boundaries.

## References
*   [PROJECT_GOALS.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/architecture/PROJECT_GOALS.md)
