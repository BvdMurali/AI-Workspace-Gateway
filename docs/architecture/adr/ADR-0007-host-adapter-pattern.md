# ADR-0007: Host Adapter Pattern

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
OS integrations (notifications, secure storage keychains, directory watching) differ extensively across macOS, Windows, and Linux.

## Decision
Abstract all platform operations behind a unified Host SDK contract interface. The Gateway Core calls this unified interface, delegating execution to the active OS implementation adapter.

## Consequences
*   **Pros**: Complete isolation of OS code from business logic. High compile stability.
*   **Cons**: Introduces bridge overhead when mapping complex native file parameters.

## Alternatives Considered
*   **Direct OS conditional checks in logic**: Rejected. Hard to read and test.

## Tradeoffs
*   Trading immediate call convenience for compile stability and cross-platform structure.

## References
*   [HOST_SDK.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/sdk/HOST_SDK.md)
