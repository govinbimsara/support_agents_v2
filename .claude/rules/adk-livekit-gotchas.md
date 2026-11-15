---
paths:
  - "app/**/*.py"
---
# ADK / LiveKit / Neon gotchas
- ADK is 2.13.x and moves fast: confirm APIs with the context7 MCP or the pinned version's source before using them; do not rely on memory (source-driven-development skill).
- `DatabaseSessionService` on Neon: pooled endpoint + NullPool (spike 1). Never write to `adk.*` tables directly.
- Voice uses ONE Live agent calling specialists as tools (no `transfer_to_agent` hand-offs). Voice model is `gemini-3.1-flash-live-preview` (preview; behaviour may change).
- Railway: outbound IPv6 is off by default; WebRTC needs IPv4 forced if the worker runs there (spike 2).
- Model Armor region is `asia-south1`. Guardrails = Model Armor + guardrail prompt + Gemini safety settings.
- Flow steps are re-executed on workflow resume; they must be idempotent (FR-TS-07, spike 17).
