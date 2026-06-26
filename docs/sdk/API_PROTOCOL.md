# REST API Protocol Specification

This document details the interface schemas, authentication requirements, versioning conventions, and streaming protocols of the **AI Workspace Gateway** REST layer.

---

## 🔒 Authentication & Headers

All REST endpoints require the following headers for validation:

```text
Authorization: Bearer <local_access_token>
Content-Type: application/json
Accept: application/json
```

### Authorization Token Lifetime
*   The `<local_access_token>` is generated locally on gateway startup and written securely to the client's OS keychain folder.
*   Token validation is verified by checking the SHA-256 hash of the received token against the temporary memory token value of the running core process.

---

## 🏷️ API Versioning

*   All REST routes follow semantic URL prefixes: `/api/v[MAJOR]/...` (e.g., `/api/v1/sessions`).
*   Breaking alterations to the JSON inputs/outputs must trigger a bump of the MAJOR suffix version.
*   Internal API patches and additions must be backward-compatible and document updates within the global changelog without altering the URL version tag.

---

## 🏗️ Detailed Endpoint Schemas

### 1. Workspace Isolation CRUD

#### `POST /api/v1/workspaces`
Creates an isolated project environment.

*   **Request Body**:
    ```json
    {
      "name": "Project Workspace",
      "config": {
        "providers": {
          "active": ["ollama"]
        }
      }
    }
    ```
*   **Response Body (`201 Created`)**:
    ```json
    {
      "id": "w1-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "name": "Project Workspace",
      "config": {
        "providers": {
          "active": ["ollama"]
        }
      },
      "createdAt": "2026-06-26T18:38:00Z"
    }
    ```

---

### 2. Session Management

#### `POST /api/v1/sessions`
Creates an agent session within a workspace.

*   **Request Body**:
    ```json
    {
      "workspaceId": "w1-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "name": "Code Review Session"
    }
    ```
*   **Response Body (`201 Created`)**:
    ```json
    {
      "id": "s1-5ff1b069-bbf2-411a-85b4-d57b321a42ef",
      "workspaceId": "w1-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "name": "Code Review Session",
      "createdAt": "2026-06-26T18:38:10Z"
    }
    ```

---

### 3. Message Post & Streaming Execution Trigger

#### `POST /api/v1/sessions/:id/messages`
Submits a message and triggers the Reasoning-Action task loops.

*   **Request Body**:
    ```json
    {
      "content": "Analyze the codebase for path traversal risks.",
      "role": "user"
    }
    ```
*   **Response Body (`202 Accepted`)**:
    ```json
    {
      "messageId": "m1-acb468ff-d0bf-4f11-8933-cb3d21f8aef2",
      "taskId": "t1-b3b38102-18c7-4340-9b30-c3d32ef3ef4f",
      "status": "enqueued"
    }
    ```

---

## 🌊 Streaming Protocol (Server-Sent Events)

When clients request streaming outputs during message generation:

### Stream Activation Route
`GET /api/v1/sessions/:id/stream?taskId=<taskId>`

The response uses standard MIME types:
```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### Event Format Schemas

#### 1. Token Stream (`event: token`)
```text
event: token
data: {"token": "Hello", "index": 0}
```

#### 2. Tool State Transition (`event: tool`)
```text
event: tool
data: {"toolName": "filesystem_read", "state": "running"}
```

#### 3. Finished Sentinel (`event: done`)
```text
event: done
data: {"messageId": "m1-acb468ff-d0bf-4f11-8933-cb3d21f8aef2", "totalTokens": 143}
```

---

## 🚦 REST Error Response Payload

If execution fails, the gateway returns uniform JSON error payloads:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested Session ID 's1-invalid' does not exist.",
    "details": {
      "resourceId": "s1-invalid",
      "resourceType": "session"
    },
    "timestamp": "2026-06-26T18:38:20Z"
  }
}
```

### Error Codes Mapping
*   `UNAUTHORIZED`: Bearer token invalid or missing.
*   `WORKSPACE_LOCKED`: Decryption keys not supplied.
*   `QUEUE_LIMIT_EXCEEDED`: Concurrency tasks maxed out.
*   `RESOURCE_NOT_FOUND`: Target workspace/session/message does not exist.
*   `VALIDATION_ERROR`: Request fields violate constraints.
