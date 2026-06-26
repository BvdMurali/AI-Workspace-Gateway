# Plugin Development Specification

This document details how to develop custom extensions (tools, custom providers, or data processors) for the **AI Workspace Gateway**.

---

## 🔄 Plugin Lifecycle

All plugins are managed by the Plugin Loader, executing within isolated sandboxes.

```mermaid
sequenceDiagram
    autonumber
    participant Engine as Gateway Core
    participant Loader as Plugin Loader
    participant Box as Sandbox (QuickJS/WASM)
    participant Registry as Tool Registry

    Engine->>Loader: Scan plugin directories
    Loader->>Loader: Read and validate manifest.json
    alt Validation Successful
        Loader->>Box: Spawn isolated worker
        Loader->>Box: Load compiled plugin bundles
        Loader->>Box: Call entrypoint `onLoad(context)`
        Box->>Registry: Register custom tools/providers
        Loader-->>Engine: Plugin Active
    else Validation Failed
        Loader-->>Engine: Log errors & isolate plugin files
    end

    Engine->>Loader: System teardown / unload plugin
    Loader->>Box: Call entrypoint `onUnload()`
    Box->>Registry: Remove registered tools
    Loader->>Box: Terminate sandbox worker thread
```

---

## 🔒 Capability & Permission Model

To protect local resources, plugins must declare access requirements in their manifest. The gateway core validates requests before granting host access.

### Permission Types Reference
*   `host:filesystem:read`: Access file reading under specific workspace subfolders.
*   `host:filesystem:write`: Access file writing under specific workspace subfolders.
*   `network:direct`: Direct internet queries (e.g., fetching a website layout). Restricted to declared host domains.
*   `storage:isolated`: Dedicated encrypted key-value store bucket for the plugin.

---

## 🧱 Plugin Manifest Schema (`manifest.json`)

All plugins must include a metadata description:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PluginManifest",
  "type": "OBJECT",
  "properties": {
    "id": { "type": "STRING", "pattern": "^[a-z0-9-]+$" },
    "name": { "type": "STRING" },
    "version": { "type": "STRING", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "description": { "type": "STRING" },
    "entryPoint": { "type": "STRING", "default": "dist/index.js" },
    "permissions": {
      "type": "ARRAY",
      "items": {
        "type": "STRING",
        "enum": [
          "host:filesystem:read",
          "host:filesystem:write",
          "network:direct",
          "storage:isolated"
        ]
      }
    },
    "networkDomains": {
      "type": "ARRAY",
      "items": { "type": "STRING" }
    }
  },
  "required": ["id", "name", "version", "entryPoint", "permissions"]
}
```

---

## 🧱 Sandbox Context & Interfaces

Inside the sandboxed runtime, plugins communicate through a secure runtime context passed into the onLoad lifecycle hook:

```typescript
export interface IsolatedFilesystem {
  readFile(relativePath: string): Promise<string>;
  writeFile(relativePath: string, content: string): Promise<void>;
}

export interface IsolatedStorage {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
}

export interface PluginContext {
  // Access to authorized OS filesystem limits
  filesystem: IsolatedFilesystem;
  
  // Access to isolated key-value store bucket
  storage: IsolatedStorage;
  
  // Register a custom function tool for LLM consumption
  registerTool(spec: {
    name: string;
    description: string;
    parameters: object; // JSON Schema matching arguments
    execute: (args: any) => Promise<any>;
  }): void;
}

// Plugin Entrypoint Contracts
export interface WorkspacePlugin {
  onLoad(context: PluginContext): Promise<void>;
  onUnload(): Promise<void>;
}
```

---

## 🛡️ Sandbox Security Architecture

1.  **Syscall Blocking**: The executing JavaScript environment (e.g., QuickJS WASM wrapper) does not contain native bindings to Node.js standard libraries (`fs`, `child_process`, `net`, `http`).
2.  **Memory Caps**: Each plugin is capped at a maximum of 64MB RAM. If memory consumption exceeds this limit, the host process terminates the sandbox instance and issues a `plugin.terminated.oom` event.
3.  **Instruction Timeout**: Tool executions are capped at 30 seconds. If a tool hangs, the scheduler interrupts the execution.
