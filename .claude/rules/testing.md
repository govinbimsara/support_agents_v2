---
paths:
  - "tests/**"
  - "app/**/*.py"
---
# Testing
- Markers: `unit` (no network), `integration` (temporary Neon branch + test S3 prefix), `behaviour` (Doc 3), `guardrail` (Doc 4).
- Write the failing test first (test-driven-development skill). Name tests with the TC-/GTS-/FR- ID they cover.
- Guardrail tests run 3x per variant (Doc 4). LLM-dependent tests assert on state, tool calls and traces, not exact wording.
- Never skip, delete, or loosen a test to reach green; fix the code or raise it with the user.
