# Tool Integration Template

This directory provides the standardized template skeleton for implementing custom execution tools for the **AI Workspace Gateway**.

---

## 🛠️ Step-by-Step Implementation

1.  **Copy this Template**: Duplicate the folder under `tools/` and rename it to your target tool (e.g., `tools/my-tool/`).
2.  **Define the Manifest**: Customize `manifest.yaml` specifying parameters using JSON Schema.
3.  **Implement the Contract**:
    *   `tool.py`: Expose the main execution class inheriting from `AbstractTool`.
4.  **Write Tests**: Build mock integration tests in the `tests/` directory verifying validation responses.

---

## 🚦 Execution Safety Constraints

*   **Sandbox Safety**: Tools must execute actions only within the permissions declared in `manifest.yaml`.
*   **Argument Validation**: Strict JSON schema checks must run *before* executing native OS calls.
*   **Execution Timeout**: Implement execution timeouts (default: 30 seconds) on all subprocess tasks to prevent thread starvation.
