# ADR-0010: SQLite Storage

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
A local-first system requires high-fidelity, relational storage supporting indexes, ACID transactions, and binary encryption-at-rest.

## Decision
Utilize SQLite (SQLCipher for desktop wraps, WASM-compiled SQLite for web/PWA targets) as the primary relational database layer.

## Consequences
*   **Pros**: Cross-platform file portability, SQLCipher encryption capabilities, zero server dependency, standard ACID semantics.
*   **Cons**: Concurrency writes are limited compared to client-server RDBMS systems.

## Alternatives Considered
*   **RxDB / IndexedDB only**: Rejected. IndexedDB lacks standard relational consistency and native encryption.
*   **JSON file storage**: Rejected due to corruption risks and lack of index query support.

## Tradeoffs
*   Trading write-heavy scaling boundaries (rare in personal workspaces) for local encryption stability.

## References
*   [DATABASE_SCHEMA.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/architecture/DATABASE_SCHEMA.md)
