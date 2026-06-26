# Project Goals

This document outlines the strategic mission, vision, long-term goals, and architectural scope boundaries of the **AI Workspace Gateway** project.

---

## 🎯 Mission & Vision

*   **Mission**: To build the definitive open-source, local-first runtime and workspace interface that empowers individuals and teams to orchestrate and execute AI workloads locally, privately, and securely.
*   **Vision**: We envision a computational environment where AI is an extension of personal and corporate workspaces, running seamlessly on local machines without exposing sensitive contextual data to centralized services unless explicitly configured.

---

## 🛠️ Core Engineering Principles

Every contribution, pull request, and design decision must align with the following principles:

1.  **Local-First, Cloud-Optional**
    *   *Default Private*: Data is stored locally on the user's disk. Database writes, indexing, and vector embeddings happen client-side.
    *   *Direct-to-API*: When using commercial cloud LLM providers, the client communicates directly with the provider APIs using locally-stored keys. No intermediary gateway or logging servers are used.
2.  **Provider Agnosticism**
    *   *Pluggable Interfaces*: The core engine does not favor any specific AI provider or model architecture. It abstracts model capabilities (chat, structured output, function calling, embeddings, image generation) behind standard adapter interfaces.
    *   *Freedom of Choice*: Users must be able to switch backend models at any time, even in the middle of a single conversation thread.
3.  **Low Friction & High Performance**
    *   *Resource Conscious*: Memory footprints should be kept small. PWA bundles must load quickly, and local database operations must not block the main UI thread.
    *   *Native Parity*: Provide native integration with the host OS (macOS and Windows) to allow system-level interactions like global shortcuts, file access, and status bar menus.
4.  **Client Diversification**
    *   The core engine must support multiple, structurally distinct client runtimes. The Progressive Web App (PWA) represents the desktop/browser interface, while the Telegram Bot / Mini App represents the quick-access chat interface.

---

## 🚀 Key Objectives

### 1. Unified Local Runtime (Phase 1 & 2)
*   Deliver a shared JavaScript/TypeScript core (`packages/core`) that handles state, memory windowing, system tool executions, and provider routing.
*   Provide a standardized database layer that is file-system based (SQLite/WASM) for local apps and IndexedDB for the PWA, ensuring full schema and migration compatibility.

### 2. Multi-OS Integration (Phase 2 & 3)
*   Support native features on **macOS** and **Windows** through the PWA desktop wrappers (e.g., app shortcuts, OS-level window management, system tray menus).
*   Plan clean support for **Linux** environments by utilizing cross-platform compatibility layers without altering the core engine.

### 3. Telegram Gateway (Phase 3)
*   Implement a secure gateway bridge that lets users chat with their local workspace via Telegram.
*   Host the Telegram Mini App (TMA) to provide a rich UI dashboard directly inside the Telegram client.

### 4. Direct Peer-to-Peer Sync (Phase 4)
*   Enable end-to-end encrypted synchronization of workspace database states between client devices (e.g., PWA on Desktop syncing to Telegram client) using P2P protocols (e.g., WebRTC, local network discovery) without a central storage server.

---

## 🙅 Non-Goals (Out of Scope)

To maintain focus and avoid scope creep, the following areas are explicitly out of scope:

*   **Centralized Database Hosting**: We will not provide a hosted, multi-tenant database for users. Sync solutions will rely on decentralized or self-hosted protocols.
*   **Model Training and Finetuning**: AI Workspace Gateway is an execution gateway, orchestrator, and interface. It does not train, fine-tune, or directly compile LLM weights.
*   **Monetization of User Context**: The project will never feature ad-insertion or telemetry tracking of user conversation contents. Any usage telemetry must be strictly opt-in and restricted to crash/performance logs.
*   **Proprietary API Adapters**: All integrations with external AI providers must remain open-source and reviewable by the community.
