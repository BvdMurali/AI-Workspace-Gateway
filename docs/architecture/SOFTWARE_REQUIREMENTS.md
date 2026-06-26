# Software Requirements Specification (SRS)

This document details the functional, non-functional, security, and OS-specific environmental requirements for the **AI Workspace Gateway**.

---

## 💻 OS-Specific System Constraints

The gateway core must support execution across heterogeneous environment environments:

### 1. macOS Runtime Requirements
*   **Operating System**: macOS Big Sur (11.0) and later. Intel and Apple Silicon (M1/M2/M3/M4) architectures.
*   **Permissions**: Require user permission for directories outside the sandboxed application bundle (e.g., accessing desktop folder contexts for RAG index ingestion).
*   **Integrations**: Hook into the macOS `LaunchAgents` system to allow auto-start on user login.

### 2. Windows Runtime Requirements
*   **Operating System**: Windows 10 (1809+) and Windows 11. x64 and ARM64 architectures.
*   **Permissions**: Execute as a medium integrity level process to access standard user directory folders without triggering Continuous User Account Control (UAC) prompts.
*   **Integrations**: Register in the Windows Registry Run key (`Software\Microsoft\Windows\CurrentVersion\Run`) for user login autostart.

### 3. Web Sandbox (Browser/PWA) Constraints
*   **Database Constraints**: In standard web browsers, fallback to IndexedDB or Origin Private File System (OPFS) WASM SQLite drivers. Local direct filesystem mounts are limited by the browser's File System Access API constraints (which require active user gesture permissions).
*   **Network Constraints**: Standard browser execution is subject to CORS restrictions. The core must run local CORS-handling headers to interact with local services like Ollama.

---

## 🔒 Security & Encryption Requirements

### 1. Master Key Derivation & Encryption-at-Rest
*   All local databases and local cache folders must be encrypted at rest using AES-256-GCM.
*   **Key Derivation**: The database encryption key must be derived from the user's master password using **Argon2id** (minimum parameters: $m=65536$ (64MB memory), $t=3$ iterations, $p=4$ parallelism lanes) or **PBKDF2-HMAC-SHA256** with at least 600,000 iterations.
*   **Key Rotation**: The database adapter must allow users to change the master password, which decrypts and re-encrypts the master key payload without requiring database rewrites.

### 2. Native Biometric Integration
*   **macOS**: Bridge connection to macOS LocalAuthentication framework to allow Touch ID to unlock the derived master key payload cached securely in the macOS Keychain.
*   **Windows**: Integrate with Windows Hello (via WinRT APIs) to resolve the master key challenge.

### 3. API Credential Isolation
*   **No Disk Storage in Plaintext**: Provider API tokens must never be written to local text logs or configuration files in plaintext.
*   **Credential Isolation**:
    *   On macOS: Save keys into the System Keychain under service label `org.ai-workspace-gateway`.
    *   On Windows: Save keys to the Windows Credential Manager under target namespace `AIWorkspaceGateway`.
    *   On Browser/PWA fallbacks: Store keys within a cryptographically isolated IndexedDB bucket, accessible only when the master database instance is unlocked.

---

## 🎯 Functional Specifications

1.  **Thread Concurrency**:
    *   The gateway must allow simultaneous execution of up to 4 concurrent agent cycles without degradation of WebSocket response latency.
    *   If concurrent runs exceed 4, subsequent requests must be held in the `Task Queue` with state set to `Enqueued`.
2.  **RAG Ingestion Limits**:
    *   Local PDF, markdown, and text document parsers must run as web workers or background child threads to prevent freezing the primary UI event loop.
    *   Maximum single document import capability: 100 MB.
3.  **Local Context Routing**:
    *   Dynamically calculate LLM context limits before dispatching prompts. The execution controller must trim or summarize the chat thread context dynamically when the current session size exceeds 90% of the provider model's input token capacity.

---

## ⚡ Non-Functional Specifications

1.  **Latency Budgets**:
    *   **Local Event Bus**: Event dispatch to listener trigger duration must be $\le 5$ milliseconds.
    *   **WebSocket Stream Startup**: Under normal disk loads, the time from receiving a chat post to streaming the first token must be $\le 200$ milliseconds for local providers (excluding LLM inference cold start).
2.  **Database Scalability**:
    *   The storage adapter must support database files up to 50 GB without performance degradation of index lookups.
    *   Perform B-tree indexing on all thread primary keys, foreign keys, and message timestamps.
3.  **Graceful Recovery**:
    *   In the event of an abrupt process crash or power loss, database operations must conform to ACID transaction boundaries, ensuring zero database file corruption on startup.
    *   Unsent messages marked as `Executing` or `Enqueued` during a crash must be updated to `Poisoned` or auto-retried on the subsequent gateway bootstrap cycle.
