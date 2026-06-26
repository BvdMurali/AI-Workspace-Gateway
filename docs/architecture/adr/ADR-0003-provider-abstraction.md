# ADR-0003: Provider Abstraction

*   **Status**: Approved
*   **Date**: 2026-06-26

## Context
Commercial AI providers release new models frequently with highly fragmented interfaces, system formats, and function calling conventions.

## Decision
Create a unified Provider SDK interface contract. All model adapters (Gemini, Anthropic, Ollama) must conform to this contract, translating proprietary payloads into gateway-standard schemas.

## Consequences
*   **Pros**: Complete provider agnosticism. Switching models in a chat session does not alter the history.
*   **Cons**: Advanced provider-specific options may be abstracted away.

## Alternatives Considered
*   **Native Integration**: Rebuilding context structures for each provider. Rejected due to maintainability issues.

## Tradeoffs
*   Trading model-specific optimizations for unified workspace execution.

## References
*   [PROVIDER_SDK.md](file:///Users/venki/Desktop/AI%20Workspace%20Gateway/docs/sdk/PROVIDER_SDK.md)
