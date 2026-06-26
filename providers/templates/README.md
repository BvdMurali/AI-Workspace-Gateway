# Provider Integration Template

This directory provides the standardized template skeleton for implementing new AI model providers for the **AI Workspace Gateway**.

---

## 🛠️ Step-by-Step Implementation

1.  **Copy this Template**: Duplicate the folder under `providers/` and rename it to your target provider (e.g., `providers/my-provider/`).
2.  **Define the Manifest**: Customize `manifest.yaml` with the target credentials schema.
3.  **Implement the Contract**:
    *   `provider.py`: Expose the main driver class inheriting from the abstract SDK.
    *   `health.py`: Write connectivity checks validating endpoint status.
    *   `capabilities.py`: Map model capability tags (e.g., text, vision, tool calling).
4.  **Write Tests**: Build mock integration tests in the `tests/` directory verifying validation responses.

---

## 🚦 Integration Constraints

*   **No Direct Shell Executions**: Provider code must not execute system commands or access host resources directly. Use the `ToolManager` context tools.
*   **Dependency Restrictions**: Only utilize packages declared in `packages/sdk` and `packages/common`. Avoid importing from other providers.
