# ADR-0002: Plugin Architecture

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
Developers require extending the gateway with custom capabilities (like custom tools, models, or data parsers) without patching core engines.

## Decision
Establish an isolated, sandboxed runtime container (QuickJS compiled to WebAssembly) that dynamically parses metadata manifests and executes plugin scripts without exposing the host OS standard libraries.

## Consequences
*   **Pros**: Extensibility, security protection from rogue code execution, hot-reloading configurations.
*   **Cons**: Resource limits restrict large plugin dependencies.

## Alternatives Considered
*   **Direct Node imports**: Rejected. Code execution is not sandboxed and risks local filesystem compromise.

## Tradeoffs
*   Trading plugin performance (WASM execution overhead) for host security isolation.

## References
*   [PLUGIN_DEVELOPMENT.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/development/PLUGIN_DEVELOPMENT.md)
