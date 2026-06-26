# Global Error Architecture Specification

This document details the global error hierarchy, propagation protocols, serialization formats, retry strategies, and recovery routines of the **AI Workspace Gateway**.

---

## 🏗️ Error Hierarchy

All runtime exceptions inherit from the base `GatewayError` class.

```text
GatewayError (Base Class)
├── WorkspaceError (Isolation violations, lock status errors)
├── ProviderError (Auth, context overflow, rate limits)
├── ToolError (Validation failures, timeout, execution crash)
├── HostError (Keychain access, file path traversal, native tray crash)
├── StorageError (SQLite corruption, full disk, transaction lock)
├── ConfigurationError (Invalid default/env yaml schemas)
├── AuthenticationError (JWT/Bearer token invalid or missing)
├── NetworkError (Gateway backend timeout, DNS resolution failure)
├── ValidationError (Incorrect HTTP body parameters)
└── TaskError (Poisoned queue items, task cancel aborts)
```

---

## 🌐 Error Propagation & Communication Mappings

Exceptions caught at boundary borders are serialized to uniform formats matching the client's connection layer.

### 1. HTTP Endpoint Mappings

| Exception Class | HTTP Status Code | Gateway Error Code |
| :--- | :--- | :--- |
| `AuthenticationError` | `401 Unauthorized` | `AUTH_TOKEN_INVALID` |
| `WorkspaceError` (Locked) | `403 Forbidden` | `WORKSPACE_IS_LOCKED` |
| `WorkspaceError` (Missing) | `404 Not Found` | `WORKSPACE_NOT_FOUND` |
| `ValidationError` | `422 Unprocessable` | `REQUEST_BODY_INVALID` |
| `ProviderError` (Quota) | `429 Too Many Requests` | `PROVIDER_RATE_LIMIT` |
| `StorageError` (Full disk)| `507 Insufficient Storage`| `DISK_SPACE_EXHAUSTED` |
| `NetworkError` | `504 Gateway Timeout` | `PROVIDER_CONNECT_TIMEOUT` |

---

### 2. WebSocket Event Mapping
When exceptions occur during real-time streaming, the connection remains open unless critical. The server transmits an `error` frame:

```json
{
  "event": "session.error",
  "sessionId": "s1-5ff1b069-bbf2-411a-85b4-d57b321a42ef",
  "taskId": "t1-b3b38102-18c7-4340-9b30-c3d32ef3ef4f",
  "timestamp": "2026-06-26T18:58:00Z",
  "payload": {
    "code": "TOOL_TIMEOUT",
    "message": "Tool 'filesystem_search' exceeded execution cap of 30 seconds.",
    "retryable": false
  }
}
```

---

## 🔄 Retry & Recovery Strategies

### 1. Retry Budget Rules
*   **Transient Errors** (e.g., `ProviderError` rate limits, `NetworkError` connection drops):
    *   The Task Queue executes up to 3 retries using **Exponential Backoff** with random jitter.
    *   Interval Calculation: $Interval = Min(30s, Base \times 2^{Attempt} + Jitter)$.
*   **Fatal Errors** (e.g., `ValidationError`, `AuthenticationError`, `HostError` path traversal):
    *   Immediate halt. The task is marked `Failed` and logged to the audit system.

### 2. Storage Recovery Routines
*   If a `StorageError` with code `SQLITE_CORRUPT` is caught during initialization:
    *   1. The engine locks database writes.
    *   2. It creates an isolated copy of the corrupt file for user retrieval.
    *   3. It restores the last successful daily binary backup (`db_backup_v[N].db`).
    *   4. It restarts the Storage Layer.
