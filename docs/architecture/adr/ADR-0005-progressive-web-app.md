# ADR-0005: Progressive Web App Client

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
Deploying native applications across desktop platforms requires distinct packaging codebases, complicating development.

## Decision
The primary desktop front-end must be built as a Progressive Web App (PWA), wrapped in thin Electron or native WebView shells for advanced OS integration features (like tray menus).

## Consequences
*   **Pros**: Shared web logic, instant updates, responsive scaling.
*   **Cons**: Browser sandbox limitations restrict direct disk read/write actions.

## Alternatives Considered
*   **Pure Native Clients (Swift/WPF)**: Rejected due to development resource requirements.

## Tradeoffs
*   Trading direct low-level OS operations (solved via Host Adapters) for frontend dev speed.

## References
*   [UI_SPEC.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/ui/UI_SPEC.md)
