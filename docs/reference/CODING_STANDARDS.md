# Codebase Coding Standards

This document establishes the official coding standards, formatting guidelines, and architectural folder boundaries of the **AI Workspace Gateway**. All code contributions must conform to these rules.

---

## 📂 Backend Gateway Folder Structure

The core service application resides under `apps/gateway/` and is divided into the following responsibility boundaries:

| Directory | Responsibility | Allowed Dependency / Imports |
| :--- | :--- | :--- |
| **`api/`** | Exposes REST/WS endpoint protocols. | `routers/`, `middleware/`, `services/` |
| **`bootstrap/`** | Orchestrates startup, config cascading, and lifecycle triggers. | `config/`, `core/`, `storage/`, `events/` |
| **`config/`** | Configuration parsers loading `configs/*.yaml` structures. | `utils/`, `packages/common/` |
| **`core/`** | Gateway Core execution orchestrator initialization. | `events/`, `storage/`, `services/` |
| **`services/`** | Implements core business services (e.g. `WorkspaceService`). | `adapters/`, `packages/core/`, `events/` |
| **`adapters/`** | Implements standard interfaces (e.g. `ProviderAdapter`). | `packages/storage/`, `host/*`, `providers/*` |
| **`middleware/`** | HTTP/WebSocket authentication, logging, and security headers. | `utils/`, `packages/auth/` |
| **`routers/`** | Sub-route controllers mapping payloads to Services. | `services/`, `utils/` |
| **`events/`** | Central Event Bus subscriber event mappings. | `packages/events/` |
| **`workers/`** | Task Queue worker loops and background processors. | `services/`, `storage/` |
| **`telemetry/`** | Anonymized usage analytics collector engines. | `packages/telemetry/` |
| **`storage/`** | SQLCipher database pool instantiator. | `packages/storage/` |
| **`security/`** | TouchID / Windows Hello client challenger hooks. | `adapters/` |
| **`utils/`** | General pure helper functions. | `packages/common/` |

---

## 📝 General Coding Conventions

### 1. Naming Conventions
*   **Files**: Use snake_case for python files (`health_check.py`), kebab-case for TS/JS client components (`task-queue.tsx`), and snake_case for SQL scripts (`v1_init.sql`).
*   **Classes**: Use PascalCase (`WorkspaceService`, `StorageAdapter`).
*   **Functions & Variables**: Use camelCase for JS/TS (`getActiveSession`), and snake_case for Python (`verify_connectivity`).
*   **Constants**: Use UPPER_SNAKE_CASE (`MAX_RETRY_ATTEMPTS`).

### 2. Type Hints (Python) & Strict Types (TypeScript)
*   **Python**: All functions must declare input and output type annotations:
    ```python
    async def get_session(self, session_id: str) -> Optional[SessionObject]:
    ```
*   **TypeScript**: Explicit types are mandatory. Do not use `any`. Compiler `strict: true` must pass.

### 3. Async/Await Rules
*   Do not write blocking calls in main execution threads. Use `async/await` and thread executors for heavy I/O operations (RAG document reading).

### 4. Logging & Exceptions
*   Always use structural JSON log formats for error output.
*   Do not catch generic exceptions (`except Exception: pass`). Always catch specific errors and wrap them in standard `GatewayError` formats.

### 5. Formatting & Import Ordering
*   **Python**: Format using black/ruff. Order imports: Standard Library $\to$ Third-Party Packages $\to$ Local Workspace Monorepo Packages.
*   **TypeScript**: Format using Prettier. Order imports: React/External Frameworks $\to$ Monorepo Packages $\to$ Local Components.
