# ADR-0009: Repository Layout

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
A local-first system contains multiple execution clients, shared SDKs, configuration schemas, tools, and OS bridges. Keeping these in separate git repositories slows down integration cycles.

## Decision
Structure the codebase as a single Monorepo separating applications (`apps/`), shared abstractions (`packages/`), provider adapters (`providers/`), runtime tools (`tools/`), OS adapters (`host/`), and documentation (`docs/`).

## Consequences
*   **Pros**: Simultaneous client updates, single issue tracker, unified integration pipelines.
*   **Cons**: Larger repository checkout size.

## Alternatives Considered
*   **Multi-Repo Setup**: Rejected. Pull requests mapping across package dependencies are too slow.

## Tradeoffs
*   Trading clone sizes for unified monorepo development velocity.

## References
*   [README.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/README.md)
