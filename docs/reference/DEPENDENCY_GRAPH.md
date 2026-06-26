# Dependency Architecture & Graph Rules

This document specifies the strict dependency hierarchy and layer isolation constraints of the **AI Workspace Gateway** codebase. All imports and package structures must conform to these rules.

---

## 🏗️ Layer Hierarchy & Mermaid Graph

The system enforces a unidirectional downward flow of imports:

```mermaid
graph TD
    subgraph Applications Layer [apps/]
        GW[apps/gateway]
        PWA[apps/pwa]
        TG[apps/telegram]
    end

    subgraph Service Orchestration Layer [apps/gateway/services/]
        WS[WorkspaceService]
        TS[TaskService]
        PS[ProviderService]
        PLS[PluginService]
        SS[SessionService]
    end

    subgraph Adapters Layer [apps/gateway/adapters/]
        AD_PROV[ProviderAdapter]
        AD_TOOL[ToolAdapter]
        AD_HOST[HostAdapter]
        AD_STORE[StorageAdapter]
    end

    subgraph Packages Layer [packages/]
        P_CORE[packages/core]
        P_SDK[packages/sdk]
        P_STOR[packages/storage]
        P_EV[packages/events]
        P_COM[packages/common]
    end

    subgraph Host OS Integration Layer [host/]
        H_MAC[host/mac]
        H_WIN[host/windows]
    end

    subgraph Core Extensibility [providers/ & tools/]
        PROVS[providers/*]
        TOOLS[tools/*]
    end

    %% Allowed Relationships
    GW --> WS
    PWA --> P_SDK
    TG --> P_SDK
    
    WS --> AD_PROV
    WS --> AD_TOOL
    WS --> AD_STORE
    WS --> AD_HOST

    AD_PROV --> P_CORE
    AD_TOOL --> P_CORE
    AD_STORE --> P_STOR
    AD_HOST --> H_MAC
    AD_HOST --> H_WIN

    PROVS --> P_SDK
    TOOLS --> P_SDK
    
    P_CORE --> P_EV
    P_STOR --> P_COM
    P_EV --> P_COM
    P_SDK --> P_COM
```

---

## 🚦 Dependency Rules Matrix

| Source Module | Target Layer | Status | Reason / Constraints |
| :--- | :--- | :--- | :--- |
| **`apps/*`** | **`packages/*`** | **ALLOWED** | Client applications consume shared abstractions and SDK helpers. |
| **`providers/*`** | **`packages/*`** | **ALLOWED** | Provider drivers must import SDK interfaces to satisfy the standard contract. |
| **`tools/*`** | **`packages/*`** | **ALLOWED** | Tools import schemas and validation helpers from shared SDK blocks. |
| **`packages/*`** | **`apps/*`** | 🚫 **FORBIDDEN** | Core libraries must never contain imports from application code (causes circular bounds). |
| **`providers/*`** | **`providers/*`**| 🚫 **FORBIDDEN** | Providers must be isolated. A provider cannot import another provider. |
| **`tools/*`** | **`providers/*`**| 🚫 **FORBIDDEN** | Tools operate independently of the underlying AI model. |
| **`host/*`** | **`providers/*`**| 🚫 **FORBIDDEN** | OS bridge adapters must remain decoupled from specific AI services. |

---

## 🔒 Layer Isolation & Egress Rules

### 1. Gateway Isolation Rules
*   **FastAPI Boundaries**: FastAPI dependencies and routes (`apps/gateway/routers/`) are strictly gateways. They must only map requests, verify tokens, and pass execution control to the corresponding `Service` classes. Under no circumstance should a router write directly to the database or invoke provider APIs.

### 2. Platform Call Restrictions
*   **No Direct Platform Calls**: The Gateway Core and Service layers must never directly call platform-specific OS APIs (e.g., Node's `process.platform`, Win32 DLL calls, or macOS AppleScript bindings).
*   **Bridges Boundary**: Any OS interaction must resolve through the `HostAdapter` which delegates calls to `host/mac/` or `host/windows/` implementation adapters.

### 3. Service vs. Adapter Boundaries
*   **Services** contain core business logic (e.g., checking user quotas, calculating prompt memory, formatting history contexts).
*   **Adapters** contain driver logic only (e.g., executing the specific HTTP request parameters of the Anthropic API, or reading/writing files via a local host handle).
