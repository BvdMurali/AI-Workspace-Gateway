# Testing Strategy Specification

This document details the multi-tiered testing matrix, coverage requirements, mocking configurations, and CI gates for the **AI Workspace Gateway**.

---

## 🧪 Testing Matrix Overview

```text
+-------------------------------------------------------------------------+
| E2E Tests (Playwright/CLI)                                              |
| -> Full workflow check: PWA UI, Gateway API, Tunnels, SQLite database.  |
+-------------------------------------------------------------------------+
| Integration Tests (Pytest/Jest)                                         |
| -> Inter-module operations, CRDT replication, secure Keychain loops.     |
+-------------------------------------------------------------------------+
| Unit Tests (Mocking Provider/Tools context)                             |
| -> Focus on isolated logic execution, state transitions, model inputs.   |
+-------------------------------------------------------------------------+
```

---

## 🏷️ Testing Definitions & Requirements

### 1. Unit Tests
*   **Target**: Isolated business functions (e.g. `PromptTrimmer`, event topic handlers).
*   **Rules**:
    *   No network operations or file system writes are permitted.
    *   Mock all provider API responses and tool results using standard fixtures.

### 2. Integration Tests
*   **Target**: Local database transactions, secure storage bridges, and event subscribers.
*   **Rules**:
    *   Operate on local SQLite instances, verifying rollback behaviors on error checks.
    *   Access actual platform adapters, verifying file watchers and keychain encryption keys.

### 3. End-to-End (E2E) Tests
*   **Target**: User scenarios across client applications.
*   **Rules**:
    *   Utilize Playwright to verify PWA chat loops (sending prompt, observing tokens stream, verifying history persistence).
    *   Verify CLI installer commands on target operating system virtual machines (macOS and Windows).

---

## 🛡️ Mocking Guidelines

To run testing sweeps without network costs or external dependencies, developers must utilize standard mock structures:

### 1. Mock Provider Template
Exposes a configurable API driver that returns preloaded text tokens or throws standard rate limit exceptions:
```python
class MockProvider(AbstractAIProvider):
    def __init__(self, response_behavior: str = "success"):
        self.behavior = response_behavior

    async def generate(self, messages, config):
        if self.behavior == "rate_limit":
            raise ProviderRateLimitError("Mock provider rate limit hit.")
        return GenerateResult(content="Mocked response payload.")
```

### 2. Mock Tool Template
Emulates local operating system actions (like listing mock folders) without making actual filesystem writes.

---

## 🚦 Coverage & CI Validation Gates

*   **Coverage Threshold**: All core packages and services must maintain $\ge 90\%$ statements and branches coverage.
*   **CI Execution Rules**:
    *   Linting and unit tests are executed automatically on every commit pull request.
    *   Integration and E2E tests are executed on release candidate runs (`vX.Y.Z` tags).
