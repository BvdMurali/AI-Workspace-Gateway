# ADR-0008: Tool Abstraction

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
AI agents execute actions on the local host filesystem. Giving models direct, uncontrolled access to terminal run loops is highly dangerous.

## Decision
Create an isolated Tool layer. AI providers cannot execute host commands directly. They must issue a tool execution request through the Tool Manager, which validates inputs against schemas and prompts the user for high-risk actions.

## Consequences
*   **Pros**: Safety control rules, parameter validation before execution, clear logging of agent actions.
*   **Cons**: Execution is bounded by the tool registry features.

## Alternatives Considered
*   **Direct LLM Command Generation**: Rejected due to catastrophic security implications.

## Tradeoffs
*   Trading agent velocity (blocking prompts for execution authorization) for host system security.

## References
*   [PLUGIN_DEVELOPMENT.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/development/PLUGIN_DEVELOPMENT.md)
