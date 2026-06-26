# ADR-0006: Telegram Companion Interface

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
Users require remote access to query their local workspace gateway from mobile environments without routing data through centralized commercial clouds.

## Decision
Support Telegram Bot and Telegram Mini App interfaces. Telegram messages are relayed securely to the user's running gateway core using end-to-end encrypted tunnels.

## Consequences
*   **Pros**: Direct mobile interface via an existing messenger, local data storage preservation.
*   **Cons**: Relies on third-party Telegram server uptime.

## Alternatives Considered
*   **Custom iOS/Android Apps**: Rejected due to app store compilation rules and distribution overhead.

## Tradeoffs
*   Trading platform independence (Telegram dependency) for friction-free mobile deployment.

## References
*   [UI_SPEC.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/ui/UI_SPEC.md)
