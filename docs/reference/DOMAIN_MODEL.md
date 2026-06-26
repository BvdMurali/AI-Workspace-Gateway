# Domain Model Specification

This document details the core business entities, structural properties, relationships, and state lifecycles of the **AI Workspace Gateway**.

---

## 📊 Entity Relationship Diagram

The core entities of the gateway relate to execution contexts and isolated storage spaces:

```mermaid
erDiagram
    WORKSPACE {
        uuid id
        string name
        json config
    }

    SESSION {
        uuid id
        uuid workspace_id
        string name
    }

    MESSAGE {
        uuid id
        uuid session_id
        string role
        string content
    }

    TASK {
        uuid id
        uuid session_id
        string action
        string status
    }

    PROVIDER {
        string name
        string endpoint
        boolean active
    }

    TOOL {
        string name
        string description
        json parameters
    }

    PLUGIN {
        string id
        string version
        array permissions
    }

    WORKSPACE ||--o{ SESSION : "isolates"
    WORKSPACE ||--o{ PROVIDER : "configures"
    SESSION ||--o{ MESSAGE : "records"
    SESSION ||--o{ TASK : "queues"
    TASK ||--o{ TOOL : "executes"
    PLUGIN ||--o{ TOOL : "exports"
```

---

## 🏷️ Domain Entity Definitions

### 1. Workspace
*   **Definition**: The primary logical isolation boundary. Holds threads, local vector slices, and decrypted model configurations.
*   **Ownership Rules**:
    *   A Workspace owns all its child Sessions, Credentials, and Vector Indices.
    *   Deleting a Workspace triggers a cascade purge of all associated child data.

### 2. Session (Chat Thread)
*   **Definition**: An active conversation log.
*   **Ownership Rules**:
    *   Belongs strictly to a parent Workspace.
    *   Holds a ordered list of Messages and associated Task logs.

### 3. Task
*   **Definition**: A background job payload queued in the Task Queue.
*   **States**: `enqueued` $\to$ `executing` $\to$ `succeeded` / `failed` / `poisoned`.

### 4. Provider
*   **Definition**: An AI model integration endpoint adapter wrapper.
*   **States**: `registered` $\to$ `configured` $\to$ `active` / `inactive`.

### 5. Tool
*   **Definition**: A function interface schema that agents invoke.
*   **Validation**: Every tool must expose a JSON Schema matching the argument types of the tool function.

### 6. Plugin
*   **Definition**: Third-party sandboxed bundle.
*   **Ownership Rules**:
    *   A plugin operates inside a sandbox and can only access the host system if authorized by the Workspace configuration boundaries.

---

## 🔄 Lifecycle Transitions Diagram

### 1. Session Thread Lifecycle
The diagram below details the thread transitions from creation to indexing:

```mermaid
stateDiagram-v2
    [*] --> Created : Session instanced
    Created --> Active : Messages received
    Active --> Suspended : Idle limit reached (15m)
    Suspended --> Active : Decryption keys provided
    Active --> Archived : User marks archived
    Archived --> [*] : User deletes thread
```

### 2. Task Processing Lifecycle
Tasks transition within the Task Queue scheduler:

```mermaid
stateDiagram-v2
    [*] --> Enqueued : Task created
    Enqueued --> Executing : Worker acquires task
    Executing --> Succeeded : Return value verified
    Executing --> Failed : Error caught
    Failed --> Retrying : Retry budget remaining
    Retrying --> Enqueued
    Failed --> Poisoned : Retry budget empty
    Succeeded --> [*]
    Poisoned --> [*]
```
