# Product Requirements Document (PRD)

This document specifies the concrete product and technical requirements for the **AI Workspace Gateway**.

---

## 📱 Client Capabilities & Matrix

AI Workspace Gateway provides two primary interfaces. Below is the feature compatibility matrix:

| Feature | Progressive Web App (PWA) | Telegram Mini App (TMA) |
| :--- | :--- | :--- |
| **Primary Platform** | Desktop (macOS, Windows, Web) | Mobile (iOS, Android, Desktop Client) |
| **Local SQLite/WASM DB** | Yes (IndexedDB fallback / WebAssembly) | Yes (LocalStorage/IndexedDB cache, Remote Sync) |
| **Offline Execution** | Yes (With local models like Ollama) | No (Requires Telegram API connectivity) |
| **OS Filesystem Access** | Yes (via File System Access API) | No (Restricted sandboxed uploads only) |
| **System Tray Integration**| Yes (via desktop wrapper wrapper/PWA) | No |
| **System Shortcuts** | Yes (Global / Browser scoped) | No |
| **Push Notifications** | Yes (Web Push API) | Yes (Telegram bot alerts) |
| **End-to-End Encrypted Sync**| Yes (Initiator / Receiver) | Yes (Receiver only) |

---

## 🔌 Offline-First Specification

To ensure a seamless user experience, the system must function without reliance on central cloud databases.

### 1. Data Persistence & Architecture
*   **Database Engine**: The application must utilize a local relational or document store schema. On desktop clients, WebAssembly SQLite is used, persisting directly to disk using origin private file system storage.
*   **Data Models**:
    *   `Workspaces`: Isolated project contexts containing prompts, histories, settings.
    *   `Sessions/Threads`: Chat sessions tied to specific workspaces.
    *   `Messages`: Individual text, code, tool invocation, or file attachments.
    *   `Credentials`: Encrypted references to API keys (never sent to third parties).
    *   `VectorIndices`: Local vector fragments for Retrieval-Augmented Generation (RAG) indexing.

### 2. Synchronization & Conflict Resolution
*   **Decentralized Sync**: Workspaces can be paired across devices. Synchronization must use an incremental sync log (CRDTs - Conflict-Free Replicated Data Types) to prevent state conflicts.
*   **Conflict Resolution Strategy**:
    *   In the case of concurrent edits to a thread, the client must apply a *Last-Write-Wins* (LWW) rule for simple fields.
    *   For message threads, messages must be ordered by local causal timestamps, appending concurrent forks as alternative path branches within the session instead of deleting historical logs.

---

## 💻 Operating System Specifications

### 🍎 macOS Requirements
*   **App Lifecycle**: Run in the menu bar/system tray as a background agent.
*   **Deep Integration**: Support drag-and-drop of local files directly onto the PWA launcher.
*   **Keychain Integration**: Securely store API credentials in the macOS Keychain using desktop app wrapper services.
*   **Resource Management**: Monitor system resource spikes during local model inference (Ollama/Llama.cpp integration) and pause background indexing tasks if CPU usage exceeds 70%.

### 🏁 Windows Requirements
*   **App Lifecycle**: System tray integration (Taskbar Notification Area) with a quick-access context menu.
*   **Integration**: Support Windows Hello for unlocking the local workspace database.
*   **Credential Manager**: Securely store API credentials in the Windows Credential Manager when running in desktop mode.
*   **Path Conventions**: Support standard Windows path notations (`C:\Users\...`) and line endings (`\r\n`) when processing local workspace documents.

### 🐧 Future Linux Roadmap Requirements
*   **Packaging**: Output Flatpak and AppImage packages.
*   **Integration**: Standard D-Bus notification structures and system tray protocol compliance (XDG StatusNotifierItem).

---

## 🔒 Security & Privacy Specification

1.  **Local Encryption**: The local SQLite database file must be encrypted at rest using SQLCipher or AES-256-GCM. The decryption key must be derived from a master password (managed via PBKDF2) or tied to OS biometrics (Touch ID / Windows Hello).
2.  **API Credential Isolation**: Under no circumstances should API keys be sent to any server other than the direct endpoints of the selected provider (e.g., `https://api.openai.com`, `https://generativelanguage.googleapis.com`).
3.  **Local Network Sandboxing**: The application must operate inside a sandbox restricting unnecessary outbound network calls. It must only communicate with approved API providers and local localhost ports (e.g., port `11434` for Ollama).
