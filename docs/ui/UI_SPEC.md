# UI & UX Interface Specification

This document details the interface layouts, responsive grid structures, control configurations, and Telegram integration patterns for the **AI Workspace Gateway** clients.

---

## 🖥️ Progressive Web App (PWA) Layout

The PWA is designed around a multi-column, collapsable grid system optimized for desktop workflows.

```text
+-----------------------------------------------------------------------------------+
| Workspace: Dev  | Session: Refactor Task | Queue: 1 Active | Tray: Online [X]     |
+-----------------+------------------------+-----------------+----------------------+
| [W1] Workspace  |                                          | [RAG Ingestion]      |
| [W2] Sandbox    |                                          | Doc: specs.pdf       |
|                 | assistant: Streamed token outputs...     | Status: 45% Indexed  |
|                 |                                          |                      |
| [Add Workspace] |                                          | [Vector Stats]       |
+-----------------+------------------------------------------+                      |
| [Session List]  |                                          |                      |
| Thread 1        |                                          |                      |
| Thread 2        |                                          |                      |
|                 |                                          |                      |
+-----------------+------------------------------------------+----------------------+
| >_ Terminal     | user: Analyze this code...               | Provider: Gemini Pro |
|                 | [Prompt Input Field]                     | Temp: 0.2            |
+-----------------+------------------------------------------+----------------------+
```

### 1. Workspace Grid Columns Layout
*   **Column 1: Workspace & Session Sidebar (Width: 260px)**
    *   *Workspace Selector Header*: Droplist displaying the current active workspace with its corresponding configuration metrics.
    *   *Session List*: Chronological list of chat threads. Right-click triggers delete, rename, and export sub-menus.
    *   *Local Terminal Button*: Launches the sandboxed command line interface at the base of the sidebar.
*   **Column 2: Central Chat Workspace (Width: Flex)**
    *   *Top Nav Bar*: Active thread title, task execution progress indicator (linked to the Task Queue), and right-panel toggle controls.
    *   *Message Stream Flow*: Rendered chat messages supporting code blocks (with syntax highlighting and copy buttons), markdown tables, and inline tool execution cards.
    *   *Input Pane*: Multi-line text field, provider model configuration selector, and file attachment drop-zone.
*   **Column 3: Workspace Tools & Metadata Sidebar (Width: 320px - Collapsable)**
    *   *Provider Selector Panel*: Details of the currently selected LLM endpoints and temperature dials.
    *   *Task Queue Panel*: Monitors RAG compilation status and background tool operations.
    *   *Vector DB Panel*: Lists local indexed documents and chunk counts.

---

## 📱 Telegram Client Interfaces

AI Workspace Gateway supports a dual Telegram strategy: a light, prompt-driven Telegram Bot interface and a high-fidelity Telegram Mini App (TMA).

### 1. Bot Command Structure
Users chat directly with their local gateway using standard bot commands relayed through secure sockets:

*   `/start`: Handshake validation. If connection token matches, establishes active session status.
*   `/workspace [name]`: Switch the current active workspace.
*   `/sessions`: List the last 5 sessions within the active workspace.
*   `/queue`: View running task status and RAG index actions.
*   `/cancel`: Halt the currently running execution task.

### 2. Telegram Mini App (TMA) Dashboard
When the user launches the Mini App, it opens a mobile-optimized dashboard:
*   **Layout Grid**: Single-column vertical scroll with tab bar navigation at the base (Chats, Workspaces, Tasks, Settings).
*   **Touch Optimizations**: Support swipe-to-delete on threads, drag-and-drop file imports via native Telegram file pickers, and biometric unlocks using the Telegram App Biometrics API.

---

## 🎛️ Primary Component Panels

### 1. Task Queue Monitor
*   **Location**: Toggleable sidebar drawer or modal overlay.
*   **UI Elements**:
    *   *Queue Density Indicator*: Running count of tasks (e.g., `3 enqueued`, `1 running`).
    *   *Task Cards*: Displaying task ID, timestamp, target action (e.g., `rag.index`), and current status indicator.
    *   *Cancel Control*: Kill button to trigger abort signals on running threads.

### 2. Local Terminal Emulator
*   **Location**: Fixed bottom-left panel of the workspace layout.
*   **UI Elements**:
    *   *Command Prompt*: Styled terminal shell (`gateway-sandbox > _`).
    *   *Sandbox Status Lights*: Red/green indicators confirming plugin sandbox status.
    *   *Restricted Command Log*: Shows standard log outputs of safe tools (like `grep`, `file_read`, and local directory lists). Direct shell commands (`sh`, `bash`) are blocked.

### 3. Provider Selector
*   **Location**: Sidebar panel.
*   **UI Elements**:
    *   *Provider Tabs*: Swappable tabs for active integrations (Ollama, Gemini, Anthropic).
    *   *Model Dropdown*: Shows available models fetched dynamically from provider runtime endpoints.
    *   *Context Slider*: Visual representation of the active context buffer size.
