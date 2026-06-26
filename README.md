# AI Workspace Gateway

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://makeapullrequest.com)
[![Semantic Versioning](https://img.shields.io/badge/semver-2.0.0-blue.svg?style=flat-square)](https://semver.org)

An open-source, local-first, provider-agnostic AI workspace platform designed for security, performance, and flexibility across macOS, Windows, and Web environments.

> [!NOTE]
> AI Workspace Gateway runs fully locally, prioritizing user ownership of data, end-to-end encryption for remote sync, and direct-to-provider interactions without middleman servers.

---

## 🎯 Mission & Vision

*   **Our Mission**: To democratize access to AI agents and models by providing an open-source, local-first runtime and workspace gateway that respects privacy, operates offline, and interfaces seamlessly with any model provider.
*   **Our Vision**: A world where individuals and organizations leverage advanced AI interfaces with absolute control over their context, history, and compute choices—free from vendor lock-in or centralized surveillance.

---

## ✨ Core Pillars

1.  **Local-First & Offline-Capable**: Your chats, database, and settings reside on your device. It runs without an active internet connection when using local models (like Ollama or Llama.cpp).
2.  **Provider-Agnostic Engine**: Seamlessly switch between commercial APIs (Gemini, OpenAI, Anthropic) and locally running models. Switch models dynamically within a single thread.
3.  **Cross-Platform Client Ecosystem**: Access your workspace via a Progressive Web App (PWA) or directly on Telegram (via Telegram Mini Apps), fully optimized for macOS, Windows, and eventually Linux.
4.  **Secure by Design**: Cryptographic local database storage, optional decentralized sync (P2P), and direct client-to-API requests with no middleman server storing API keys.

---

## 📂 Repository Directory Structure

```text
ai-workspace-gateway/
├── .github/                 # GitHub Issue/PR Templates & CI Workflows
├── apps/                    # Core Applications
│   ├── gateway/             # Backend service (FastAPI)
│   ├── pwa/                 # Progressive Web App client
│   └── telegram/            # Telegram bot client
├── packages/                # Shared Reusable Libraries (Abstractions Only)
│   ├── core/                # Core Orchestration Interfaces
│   ├── common/              # Shared types and utilities
│   ├── events/              # Event Bus definitions
│   ├── sdk/                 # Internal integration SDK modules
│   ├── storage/             # Encrypted DB/Vector bindings
│   ├── auth/                # Authentication adapters
│   └── telemetry/           # Anonymized analytics
├── providers/               # Provider Implementations Only (Claude, Codex, Mock, etc.)
├── tools/                   # Extensible Execution Tools (Terminal, FS, Git, Docker, etc.)
├── host/                    # Platform-Specific Bridges (macOS, Windows)
├── plugins/                 # Sandboxed Third-Party Plugins Folder
├── configs/                 # Configuration Profiles (default, dev, prod)
├── docs/                    # Reorganized Architecture & System Documentation
│   ├── architecture/        # Core Design Decisions
│   ├── sdk/                 # SDK API Integration Specs
│   ├── deployment/          # Installers and Network Tunnels Specs
│   ├── security/            # Threat Model and Sandboxing Specs
│   ├── ui/                  # UI Responsive Layout Specs
│   └── development/         # Roadmaps and Codebase Rules
├── examples/                # Example Integration Scripts
├── installer/               # Packaging Scripts (macOS, Windows)
├── schemas/                 # JSON Schemas (workspace, task, provider, event)
├── assets/                  # UI static assets (logos, icons)
├── tests/                   # Segmented Testing Matrix (unit, integration, e2e, fixtures)
├── scripts/                 # Utility Build Scripts
├── README.md                # Portal Index (Root)
├── ROADMAP.md               # Release Milestones (Root)
├── CHANGELOG.md             # Keep a Changelog details (Root)
└── CONTRIBUTING.md          # Code contribution guides (Root)
```

---

## 🏗️ Architecture & Layer Overview

The monorepo separates runtime orchestration, local data synchronization, provider integration, and client user interfaces into distinct architectural layers:

```text
       Clients (PWA / Telegram Mini App)
                  ↓
       Gateway Layer (REST / WebSockets API)
                  ↓
       Services Layer (Business Logic Orchestration)
                  ↓
       Adapters Layer (Platform & Provider Abstractions)
                  ↓
       Operating System & Native APIs
```

### Architectural Divisions

1.  **Clients Layer**: Communicates with the gateway strictly via standard REST and WebSockets.
2.  **Gateway Core**: Orchestrates connection lifetimes, request routing, and initializes services. Does not implement business logic.
3.  **Services Layer**: Houses core business logic. Modules include:
    *   `WorkspaceService`: Manages isolated user data spaces.
    *   `TaskService`: Handles task queues and worker allocations.
    *   `ProviderService`: Manages the available AI model registry.
    *   `PluginService`: Evaluates permissions and boots sandboxed code.
    *   `NotificationService`: Triggers user alerts.
    *   `SessionService`: Tracks threads and memory states.
4.  **Adapters Layer**: Standardizes access to concrete external components:
    *   `ProviderAdapter`: Interacts with Gemini, OpenAI, Ollama, etc.
    *   `ToolAdapter`: Executes registered functions (file system access, local terminal running).
    *   `HostAdapter`: Accesses operating system features (Keychain, Credential Manager, notifications).
    *   `StorageAdapter`: Handles database encryption (SQLCipher) and vector indexing.
    *   `AuthenticationAdapter`: Resolves token challenge validations.

For a deeper dive into the architectural systems, see [ARCHITECTURE.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/architecture/ARCHITECTURE.md).

---

## 🛠️ Getting Started

### Prerequisites

*   Node.js (LTS version v20+)
*   PNPM (v9+)
*   Git

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/ai-workspace-gateway.git
cd ai-workspace-gateway

# Install monorepo dependencies
pnpm install

# Run development servers
pnpm dev
```

For more detailed developer guidelines, please refer to [CONTRIBUTING.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/CONTRIBUTING.md).

---

## 🛡️ Governance & Security

*   **Branching & Releasing**: We follow a trunk-based workflow with SemVer versioning. Release automation updates package versions on merge to `main`. Read more in [CONTRIBUTING.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/CONTRIBUTING.md).
*   **Security Policies**: If you discover a vulnerability, do not open a public issue. Follow the instructions in [SECURITY.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/security/SECURITY.md) to report privately.

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
